from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import BlockedError
from .integrity import evaluator_hash, sha256_file
from .io import dump_json, load_config


def _verify_integrity(metrics: dict[str, Any]) -> None:
    recorded = metrics.get("integrity", {}).get("before")
    after = metrics.get("integrity", {}).get("after")
    if not recorded or recorded != after:
        raise BlockedError("EVALUATION_CONTRACT_MUTATED", "missing or inconsistent integrity snapshots")
    for name, item in recorded.get("files", {}).items():
        path = Path(item["path"])
        if not path.is_file() or sha256_file(path) != item.get("sha256"):
            raise BlockedError("EVALUATION_CONTRACT_MUTATED", f"{name} changed after evaluation")
    if evaluator_hash() != recorded.get("evaluator", {}).get("sha256"):
        raise BlockedError("EVALUATOR_INTEGRITY_FAILURE", "evaluator code changed after evaluation")


def gate(metrics: dict[str, Any], config_path: Path, output_path: Path | None = None, trust_anchor: Path | None = None, trust_anchor_sha256: str | None = None, audit_log: Path | None = None) -> dict:
    _verify_integrity(metrics)
    config = load_config(config_path)
    recorded_config = metrics["integrity"]["before"]["files"]["config"]
    if str(config_path.resolve()) != recorded_config["path"] or sha256_file(config_path) != recorded_config["sha256"]:
        raise BlockedError("EVALUATION_CONTRACT_MUTATED", "gate configuration differs from evaluated configuration")
    # Never trust an editable metrics artifact. Recompute from the immutable
    # paths recorded by evaluate and compare the complete decision evidence.
    from tempfile import TemporaryDirectory
    from .evaluator import evaluate
    files = metrics["integrity"]["before"]["files"]
    manifest = Path(files["corpus_manifest"]["path"]) if "corpus_manifest" in files else None
    recorded_anchor = Path(files["trust_anchor"]["path"]) if "trust_anchor" in files else None
    if (recorded_anchor.resolve() if recorded_anchor else None) != (trust_anchor.resolve() if trust_anchor else None):
        raise BlockedError("TRUST_ANCHOR_MISMATCH", "gate trust anchor differs from evaluated trust anchor")
    recorded_audit = Path(files["audit_log"]["path"]) if "audit_log" in files else None
    if (recorded_audit.resolve() if recorded_audit else None) != (audit_log.resolve() if audit_log else None):
        raise BlockedError("AUDIT_ATTESTATION_MISMATCH", "gate audit evidence differs from evaluated audit evidence")
    with TemporaryDirectory() as temp:
        recomputed = evaluate(
            Path(files["gold"]["path"]), Path(files["run"]["path"]),
            config_path, Path(temp), manifest, trust_anchor, trust_anchor_sha256, audit_log,
        )
    for field in ("query_count", "evaluated_query_count", "query_coverage", "metrics", "per_query"):
        if metrics.get(field) != recomputed.get(field):
            raise BlockedError("METRICS_INTEGRITY_FAILURE", f"metrics artifact field {field} differs from recomputation")
    primary = str(config["evaluation"]["primary_k"])
    retrieval = metrics.get("metrics", {}).get("retrieval", {}).get(primary)
    if not retrieval:
        raise BlockedError("MISSING_EVIDENCE", f"metrics do not contain primary K={primary}")
    observed = metrics["metrics"]
    checks = []
    mapping = {
        "hit_rate_at_k": retrieval["hit_rate"],
        "recall_at_k": retrieval["recall"],
        "mrr_at_k": retrieval["mrr"],
        "ndcg_at_k": retrieval["ndcg"],
        "citation_precision": observed["citation_precision"],
        "citation_recall": observed["citation_recall"],
        "abstention_accuracy": observed["abstention_accuracy"],
    }
    for name, threshold in config["thresholds"].items():
        value = mapping[name]
        checks.append({"name": name, "observed": value, "operator": ">=", "required": threshold, "passed": value >= threshold})
    limit_mapping = {"p95_latency_ms": observed["p95_latency_ms"], "mean_cost_usd": observed["mean_cost_usd"]}
    for name, limit in config["limits"].items():
        value = limit_mapping[name]
        checks.append({"name": name, "observed": value, "operator": "<=", "required": limit, "passed": value <= limit})
    risk = config.get("risk_profile", "R0")
    dimensions = {
        "retrieval": "PASS" if all(c["passed"] for c in checks if c["name"] in {"hit_rate_at_k", "recall_at_k", "mrr_at_k", "ndcg_at_k"}) else "FAIL",
        "evidence": "PASS" if all(c["passed"] for c in checks if c["name"] in {"citation_precision", "citation_recall"}) else "FAIL",
        "operations": "PASS" if all(c["passed"] for c in checks if c["name"] in {"p95_latency_ms", "mean_cost_usd"}) else "FAIL",
        "authorization": "NOT_EVALUATED",
        "privacy_security": "NOT_EVALUATED",
    }
    if risk in {"R2", "R3"}:
        enterprise = config["enterprise"]
        enterprise_checks = [
            {"name": "authorization_accuracy", "observed": observed["authorization_accuracy"], "operator": ">=", "required": enterprise["authorization_accuracy"], "passed": observed["authorization_accuracy"] is not None and observed["authorization_accuracy"] >= enterprise["authorization_accuracy"]},
            {"name": "audit_completeness", "observed": observed["audit_completeness"], "operator": ">=", "required": enterprise["audit_completeness"], "passed": observed["audit_completeness"] is not None and observed["audit_completeness"] >= enterprise["audit_completeness"]},
            {"name": "critical_security_failures", "observed": observed["critical_security_failures"], "operator": "<=", "required": enterprise["max_critical_security_failures"], "passed": observed["critical_security_failures"] <= enterprise["max_critical_security_failures"]},
        ]
        checks.extend(enterprise_checks)
        dimensions["authorization"] = "PASS" if enterprise_checks[0]["passed"] else "FAIL"
        dimensions["privacy_security"] = "PASS" if all(c["passed"] for c in enterprise_checks[1:]) else "FAIL"
    verdict = "PASS" if all(c["passed"] for c in checks) else "FAIL"
    if risk == "R3" and verdict == "PASS":
        verdict = "BLOCKED"
        dimensions["human_approval"] = "REQUIRED"
        blockers = ["HUMAN_APPROVAL_REQUIRED"]
    else:
        dimensions["human_approval"] = "NOT_REQUIRED" if risk != "R3" else "REQUIRED"
        blockers = []
    result = {"schema_version": "3.0", "risk_profile": risk, "verdict": verdict, "dimensions": dimensions, "checks": checks, "blockers": blockers}
    if output_path:
        dump_json(output_path, result)
    return result
