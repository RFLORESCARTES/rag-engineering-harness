from __future__ import annotations

import math
import statistics
from pathlib import Path
from typing import Any

from .errors import BlockedError
from .integrity import snapshot
from .io import dump_json, load_config, load_jsonl


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


def _dcg(grades: list[float]) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(grades))


def evaluate(gold_path: Path, run_path: Path, config_path: Path, out_dir: Path) -> dict:
    before = snapshot(gold_path, run_path, config_path)
    config = load_config(config_path)
    gold = _unique_ids(load_jsonl(gold_path), "gold")
    run = _unique_ids(load_jsonl(run_path), "run")
    for row in gold.values():
        _validate_gold(row)
    for row in run.values():
        _validate_run(row, bool(config["evaluation"].get("require_provenance", True)))
    missing = sorted(gold.keys() - run.keys())
    unknown = sorted(run.keys() - gold.keys())
    if unknown or (missing and config["evaluation"].get("require_complete_query_set", True)):
        raise BlockedError("QUERY_SET_MISMATCH", f"missing={missing}; unknown={unknown}")

    ks = config["evaluation"]["k_values"]
    accum = {k: {m: [] for m in ("hit_rate", "recall", "precision", "mrr", "ndcg")} for k in ks}
    citation_precision, citation_recall, abstention, latency, cost, per_query = [], [], [], [], [], []
    for qid, expected in gold.items():
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
        citations = set(actual.get("citations", []))
        citation_precision.append(len(citations & relevant) / len(citations) if citations else float(not relevant))
        citation_recall.append(len(citations & relevant) / len(relevant) if relevant else float(not citations))
        abstention.append(float(actual["abstained"] == (not expected["answerable"])))
        latency.append(float(actual["latency_ms"]))
        cost.append(float(actual["cost_usd"]))
        per_query.append({"query_id": qid, "retrieval": q_metrics})

    aggregate = {}
    for k in ks:
        aggregate[str(k)] = {name: statistics.fmean(values) for name, values in accum[k].items()}
    ordered_latency = sorted(latency)
    p95_index = max(0, math.ceil(0.95 * len(ordered_latency)) - 1)
    metrics = {
        "schema_version": "1.0",
        "status": "EVALUATED",
        "query_count": len(gold),
        "metrics": {
            "retrieval": aggregate,
            "citation_precision": statistics.fmean(citation_precision),
            "citation_recall": statistics.fmean(citation_recall),
            "abstention_accuracy": statistics.fmean(abstention),
            "p95_latency_ms": ordered_latency[p95_index],
            "mean_cost_usd": statistics.fmean(cost),
        },
        "per_query": per_query,
        "integrity": {"before": before},
    }
    after = snapshot(gold_path, run_path, config_path)
    metrics["integrity"]["after"] = after
    if before != after:
        raise BlockedError("EVALUATION_CONTRACT_MUTATED", "evaluation inputs or evaluator changed during execution")
    dump_json(out_dir / "metrics.json", metrics)
    return metrics
