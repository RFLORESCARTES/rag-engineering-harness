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


def gate(metrics: dict[str, Any], config_path: Path, output_path: Path | None = None) -> dict:
    _verify_integrity(metrics)
    config = load_config(config_path)
    recorded_config = metrics["integrity"]["before"]["files"]["config"]
    if str(config_path.resolve()) != recorded_config["path"] or sha256_file(config_path) != recorded_config["sha256"]:
        raise BlockedError("EVALUATION_CONTRACT_MUTATED", "gate configuration differs from evaluated configuration")
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
    verdict = "PASS" if all(c["passed"] for c in checks) else "FAIL"
    result = {"schema_version": "1.0", "verdict": verdict, "checks": checks, "blockers": []}
    if output_path:
        dump_json(output_path, result)
    return result
