from __future__ import annotations

import math
import statistics
import unicodedata
from pathlib import Path
from typing import Any

from .errors import BlockedError
from .integrity import snapshot
from .io import dump_json, load_config, load_jsonl
from .trust import verify_trust_anchor


def _security_text(value: str) -> str:
    """Canonicalize common Unicode evasions before deterministic marker checks."""
    normalized = unicodedata.normalize("NFKC", value)
    normalized = "".join("-" if unicodedata.category(char) == "Pd" else char for char in normalized)
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Cf")
    return " ".join(normalized.casefold().split())


def _validate_manifest_access(row: dict[str, Any]) -> None:
    tenant = row.get("tenant_id")
    allowed = row.get("allowed_tenants")
    scope = row.get("scope")
    if isinstance(tenant, str) and tenant.strip():
        return
    if scope == "SHARED" and isinstance(allowed, list) and allowed and all(isinstance(x, str) and x.strip() for x in allowed):
        return
    raise BlockedError("MISSING_ACCESS_METADATA", f"{row['doc_id']}: require tenant_id or explicit SHARED allowed_tenants")


def _unique_ids(rows: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    indexed = {}
    for row in rows:
        qid = row.get("query_id")
        if not isinstance(qid, str) or not qid.strip():
            raise BlockedError("INVALID_SCHEMA", f"{label}: query_id must be a non-empty string")
        if qid in indexed:
            raise BlockedError("INVALID_GOLD_SET" if label == "gold" else "INVALID_RUN", f"{label}: duplicate query_id {qid}")
        indexed[qid] = row
    return indexed


def _validate_gold(row: dict[str, Any]) -> None:
    answerable = row.get("answerable", True)
    relevant = row.get("relevant_doc_ids")
    if not isinstance(answerable, bool) or not isinstance(relevant, list) or any(not isinstance(x, str) for x in relevant):
        raise BlockedError("INVALID_GOLD_SET", "gold answerable/relevant_doc_ids have invalid types")
    if len(set(relevant)) != len(relevant):
        raise BlockedError("INVALID_GOLD_SET", "gold relevant_doc_ids contain duplicates")
    if answerable and not relevant:
        raise BlockedError("INVALID_GOLD_SET", "answerable query has no relevant documents")
    grades = row.get("graded_relevance", {})
    if not isinstance(grades, dict) or any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0 for v in grades.values()):
        raise BlockedError("INVALID_GOLD_SET", "graded_relevance must contain finite non-negative values")
    if any(doc in grades and grades[doc] <= 0 for doc in relevant):
        raise BlockedError("INVALID_GOLD_SET", "relevant documents must have positive graded_relevance")
    evidence = row.get("evidence", [])
    if not isinstance(evidence, list):
        raise BlockedError("INVALID_GOLD_SET", "evidence must be a list")
    evidence_ids = []
    for item in evidence:
        if not isinstance(item, dict) or not isinstance(item.get("evidence_id"), str) or not isinstance(item.get("doc_id"), str):
            raise BlockedError("INVALID_GOLD_SET", "evidence items need string evidence_id and doc_id")
        evidence_ids.append(item["evidence_id"])
    if len(evidence_ids) != len(set(evidence_ids)):
        raise BlockedError("INVALID_GOLD_SET", "evidence IDs must be unique per query")
    expected_action = row.get("expected_action")
    if expected_action is not None and expected_action not in {"ANSWER", "ABSTAIN_INSUFFICIENT_EVIDENCE", "ABSTAIN_CONFLICTING_EVIDENCE", "DENY_ACCESS", "DENY_CROSS_TENANT", "DENY_PURPOSE", "BLOCKED_STALE_POLICY"}:
        raise BlockedError("INVALID_GOLD_SET", "invalid expected_action")
    for field in ("forbidden_doc_ids", "forbidden_output_markers"):
        value = row.get(field, [])
        if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
            raise BlockedError("INVALID_GOLD_SET", f"{field} must be a list of non-empty strings")


def _validate_run(row: dict[str, Any], require_provenance: bool) -> None:
    retrieved = row.get("retrieved")
    if not isinstance(retrieved, list):
        raise BlockedError("INVALID_RUN", "retrieved must be a list")
    doc_ids, ranks = [], []
    for item in retrieved:
        if not isinstance(item, dict) or not isinstance(item.get("doc_id"), str) or not isinstance(item.get("rank"), int):
            raise BlockedError("INVALID_RUN", "each retrieved item needs string doc_id and integer rank")
        doc_ids.append(item["doc_id"])
        ranks.append(item["rank"])
    if len(doc_ids) != len(set(doc_ids)) or sorted(ranks) != list(range(1, len(ranks) + 1)):
        raise BlockedError("INVALID_RUN", "document IDs must be unique and ranks contiguous from 1")
    if any(not isinstance(x, str) for x in row.get("citations", [])):
        raise BlockedError("INVALID_RUN", "citations must be a list of document IDs")
    for field in ("latency_ms", "cost_usd"):
        value = row.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
            raise BlockedError("INVALID_RUN", f"{field} must be finite and non-negative")
    if not isinstance(row.get("abstained"), bool):
        raise BlockedError("INVALID_RUN", "abstained must be boolean")
    if require_provenance:
        provenance = row.get("provenance")
        if not isinstance(provenance, dict) or not all(provenance.get(k) for k in ("system", "run_id", "created_at")):
            raise BlockedError("MISSING_PROVENANCE", "provenance needs system, run_id, and created_at")


def _validate_enterprise_run(row: dict[str, Any]) -> None:
    if row.get("decision") not in {"ANSWER", "ABSTAIN_INSUFFICIENT_EVIDENCE", "ABSTAIN_CONFLICTING_EVIDENCE", "DENY_ACCESS", "DENY_CROSS_TENANT", "DENY_PURPOSE", "BLOCKED_STALE_POLICY", "BLOCKED_SYSTEM_FAILURE"}:
        raise BlockedError("INVALID_RUN", "enterprise run requires a valid decision")
    audit = row.get("audit")
    if not isinstance(audit, dict):
        raise BlockedError("MISSING_AUDIT_EVIDENCE", "enterprise run requires audit evidence")


def _dcg(grades: list[float]) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(grades))


def evaluate(gold_path: Path, run_path: Path, config_path: Path, out_dir: Path, corpus_manifest: Path | None = None, trust_anchor: Path | None = None, trust_anchor_sha256: str | None = None, audit_log: Path | None = None) -> dict:
    config = load_config(config_path)
    if config["evaluation"].get("require_corpus_manifest", False) and corpus_manifest is None:
        raise BlockedError("MISSING_CORPUS_MANIFEST", "a corpus manifest is required by configuration")
    if config.get("enterprise", {}).get("require_external_audit", False) and audit_log is None:
        raise BlockedError("MISSING_AUDIT_EVIDENCE", "an independently captured audit log is required")
    if config.get("integrity", {}).get("require_trust_anchor", False):
        verify_trust_anchor(trust_anchor, trust_anchor_sha256, gold_path, config_path, corpus_manifest, audit_log, config.get("risk_profile", "R0"))
    before = snapshot(gold_path, run_path, config_path, corpus_manifest, trust_anchor, audit_log)
    gold = _unique_ids(load_jsonl(gold_path), "gold")
    run = _unique_ids(load_jsonl(run_path), "run")
    audit_by_decision: dict[str, dict[str, Any]] = {}
    if audit_log is not None:
        audit_rows = load_jsonl(audit_log)
        for audit_row in audit_rows:
            decision_id = audit_row.get("decision_id")
            if not isinstance(decision_id, str) or not decision_id or decision_id in audit_by_decision:
                raise BlockedError("INVALID_AUDIT_EVIDENCE", "audit decision_id values must be non-empty and unique")
            audit_by_decision[decision_id] = audit_row
    manifest_ids: set[str] | None = None
    manifest_by_id: dict[str, dict[str, Any]] = {}
    if corpus_manifest is not None:
        manifest_rows = load_jsonl(corpus_manifest)
        ids = [row.get("doc_id") for row in manifest_rows]
        if any(not isinstance(x, str) or not x for x in ids) or len(ids) != len(set(ids)):
            raise BlockedError("INVALID_CORPUS_MANIFEST", "manifest doc_id values must be non-empty and unique")
        manifest_ids = set(ids)
        manifest_by_id = {row["doc_id"]: row for row in manifest_rows}
        if config.get("risk_profile", "R0") in {"R1", "R2", "R3"}:
            for row in manifest_rows:
                _validate_manifest_access(row)
        if config["evaluation"].get("require_content_hashes", False):
            for row in manifest_rows:
                digest = row.get("sha256")
                if not isinstance(digest, str) or len(digest) != 64:
                    raise BlockedError("MISSING_CORPUS_HASH", f"{row['doc_id']}: valid sha256 is required")
    for row in gold.values():
        _validate_gold(row)
        if config["evaluation"].get("require_evidence", False) and row.get("answerable", True) and not row.get("evidence"):
            raise BlockedError("MISSING_EVIDENCE", f"{row['query_id']}: answerable query has no evidence records")
        if manifest_ids is not None:
            unknown_docs = set(row["relevant_doc_ids"]) - manifest_ids
            unknown_evidence_docs = {x["doc_id"] for x in row.get("evidence", [])} - manifest_ids
            if unknown_docs or unknown_evidence_docs:
                raise BlockedError("CORPUS_REFERENCE_MISMATCH", f"{row['query_id']}: unknown corpus documents {sorted(unknown_docs | unknown_evidence_docs)}")
    for row in run.values():
        _validate_run(row, bool(config["evaluation"].get("require_provenance", True)))
        if config.get("risk_profile", "R0") in {"R2", "R3"}:
            _validate_enterprise_run(row)
            if config.get("enterprise", {}).get("require_external_audit", False):
                observed_audit = row["audit"]
                trusted_audit = audit_by_decision.get(observed_audit.get("decision_id"))
                observed = {
                    **observed_audit,
                    "query_id": row.get("query_id"),
                    "decision": row.get("decision"),
                    "run_id": row.get("provenance", {}).get("run_id"),
                    "system": row.get("provenance", {}).get("system"),
                }
                fields = ("query_id", "actor_id", "tenant_id", "policy_id", "decision_id", "decision", "timestamp", "run_id", "system")
                if trusted_audit is None or any(trusted_audit.get(field) != observed.get(field) for field in fields):
                    raise BlockedError("AUDIT_ATTESTATION_MISMATCH", f"{row['query_id']}: run audit is not corroborated by trusted audit evidence")
    missing = sorted(gold.keys() - run.keys())
    unknown = sorted(run.keys() - gold.keys())
    if unknown or (missing and config["evaluation"].get("require_complete_query_set", True)):
        raise BlockedError("QUERY_SET_MISMATCH", f"missing={missing}; unknown={unknown}")
    evaluated_ids = [qid for qid in gold if qid in run]
    if not evaluated_ids:
        raise BlockedError("MISSING_EVIDENCE", "run contains no evaluable gold queries")

    ks = config["evaluation"]["k_values"]
    accum = {k: {m: [] for m in ("hit_rate", "recall", "precision", "mrr", "ndcg")} for k in ks}
    citation_precision, citation_recall, abstention, latency, cost, per_query = [], [], [], [], [], []
    authorization, audit_scores = [], []
    cross_tenant_leakage_count = forbidden_output_count = 0
    for qid in evaluated_ids:
        expected = gold[qid]
        actual = run[qid]
        relevant = set(expected["relevant_doc_ids"])
        ranked = [x["doc_id"] for x in sorted(actual["retrieved"], key=lambda x: x["rank"])]
        grades = {doc: float(v) for doc, v in expected.get("graded_relevance", {}).items()}
        for doc in relevant:
            grades.setdefault(doc, 1.0)
        q_metrics = {}
        if expected["answerable"]:
            for k in ks:
                top = ranked[:k]
                hits = [doc for doc in top if doc in relevant]
                hit_rate = float(bool(hits))
                recall = len(hits) / len(relevant)
                precision = len(hits) / k
                rr = next((1.0 / (i + 1) for i, doc in enumerate(top) if doc in relevant), 0.0)
                actual_dcg = _dcg([grades.get(doc, 0.0) for doc in top])
                ideal_dcg = _dcg(sorted(grades.values(), reverse=True)[:k])
                ndcg = actual_dcg / ideal_dcg
                vals = {"hit_rate": hit_rate, "recall": recall, "precision": precision, "mrr": rr, "ndcg": ndcg}
                q_metrics[str(k)] = vals
                for name, value in vals.items():
                    accum[k][name].append(value)
        else:
            q_metrics["not_applicable"] = "unanswerable_query"
        citation_level = config["evaluation"].get("citation_level", "document")
        if citation_level == "evidence":
            expected_citations = {x["evidence_id"] for x in expected.get("evidence", [])}
        else:
            expected_citations = relevant
        citations = set(actual.get("citations", []))
        citation_precision.append(len(citations & expected_citations) / len(citations) if citations else float(not expected_citations))
        citation_recall.append(len(citations & expected_citations) / len(expected_citations) if expected_citations else float(not citations))
        abstention.append(float(actual["abstained"] == (not expected["answerable"])))
        expected_action = expected.get("expected_action")
        if expected_action is not None:
            authorization.append(float(actual.get("decision") == expected_action))
        forbidden_docs = set(expected.get("forbidden_doc_ids", []))
        leaked_docs = sorted(forbidden_docs & set(ranked))
        if config.get("risk_profile", "R0") in {"R2", "R3"} and manifest_by_id:
            actor_tenant = actual.get("audit", {}).get("tenant_id")
            unknown_retrieved = [doc for doc in ranked if doc not in manifest_by_id]
            if unknown_retrieved:
                raise BlockedError("CORPUS_REFERENCE_MISMATCH", f"retrieved documents absent from manifest: {unknown_retrieved}")
            tenant_leaks = []
            for doc in ranked:
                metadata = manifest_by_id[doc]
                allowed = metadata.get("allowed_tenants", []) if metadata.get("scope") == "SHARED" else []
                if metadata.get("tenant_id") != actor_tenant and actor_tenant not in allowed:
                    tenant_leaks.append(doc)
            leaked_docs = sorted(set(leaked_docs) | set(tenant_leaks))
        cross_tenant_leakage_count += len(leaked_docs)
        answer_text = actual.get("answer", "")
        if not isinstance(answer_text, str):
            raise BlockedError("INVALID_RUN", "answer must be a string when present")
        normalized_answer = _security_text(answer_text)
        matched_markers = [marker for marker in expected.get("forbidden_output_markers", []) if _security_text(marker) in normalized_answer]
        forbidden_output_count += len(matched_markers)
        if config.get("risk_profile", "R0") in {"R2", "R3"}:
            audit = actual.get("audit", {})
            mandatory_audit = ("actor_id", "tenant_id", "policy_id", "decision_id", "timestamp")
            audit_scores.append(sum(bool(audit.get(field)) for field in mandatory_audit) / len(mandatory_audit))
        latency.append(float(actual["latency_ms"]))
        cost.append(float(actual["cost_usd"]))
        per_query.append({"query_id": qid, "retrieval": q_metrics, "security": {"expected_action": expected_action, "observed_action": actual.get("decision"), "forbidden_documents_retrieved": leaked_docs, "forbidden_output_markers": matched_markers}})

    aggregate = {}
    for k in ks:
        aggregate[str(k)] = {name: statistics.fmean(values) for name, values in accum[k].items()}
    ordered_latency = sorted(latency)
    p95_index = max(0, math.ceil(0.95 * len(ordered_latency)) - 1)
    metrics = {
        "schema_version": "2.0",
        "status": "EVALUATED",
        "query_count": len(gold),
        "evaluated_query_count": len(evaluated_ids),
        "query_coverage": len(evaluated_ids) / len(gold),
        "metrics": {
            "retrieval": aggregate,
            "citation_precision": statistics.fmean(citation_precision),
            "citation_recall": statistics.fmean(citation_recall),
            "abstention_accuracy": statistics.fmean(abstention),
            "p95_latency_ms": ordered_latency[p95_index],
            "mean_cost_usd": statistics.fmean(cost),
            "authorization_accuracy": statistics.fmean(authorization) if authorization else None,
            "audit_completeness": statistics.fmean(audit_scores) if audit_scores else None,
            "cross_tenant_leakage_count": cross_tenant_leakage_count,
            "forbidden_output_count": forbidden_output_count,
            "critical_security_failures": cross_tenant_leakage_count + forbidden_output_count,
        },
        "per_query": per_query,
        "integrity": {"before": before},
    }
    after = snapshot(gold_path, run_path, config_path, corpus_manifest, trust_anchor, audit_log)
    metrics["integrity"]["after"] = after
    if before != after:
        raise BlockedError("EVALUATION_CONTRACT_MUTATED", "evaluation inputs or evaluator changed during execution")
    dump_json(out_dir / "metrics.json", metrics)
    return metrics
