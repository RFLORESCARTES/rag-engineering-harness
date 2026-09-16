from __future__ import annotations


def release_gate(metrics: dict, config: dict) -> dict:
    integrity = metrics.get("integrity", {})
    blockers = []
    if integrity.get("missing_run_ids"):
        blockers.append("missing_run_cases")
    primary = str(config["primary_cutoff"])
    observed = metrics.get("aggregate", {}).get(primary)
    if observed is None:
        blockers.append("missing_primary_retrieval_metrics")
    if blockers:
        return {"status": "BLOCKED", "blockers": blockers, "checks": []}

    thresholds = config["release_gate"]["retrieval"]
    mapping = {"hit_rate_at_k": "hit_rate", "recall_at_k": "recall", "mrr_at_k": "mrr", "ndcg_at_k": "ndcg"}
    checks = []
    for threshold_name, metric_name in mapping.items():
        target = thresholds.get(threshold_name)
        if target is None:
            continue
        value = observed[metric_name]
        checks.append({"name": threshold_name, "value": value, "threshold": target, "pass": value >= target})

    abst_target = config["release_gate"].get("abstention", {}).get("unanswerable_safe_rate")
    abst_value = metrics.get("abstention", {}).get("unanswerable_safe_rate")
    if abst_target is not None:
        if abst_value is None:
            blockers.append("abstention_not_measured")
        else:
            checks.append({"name": "unanswerable_safe_rate", "value": abst_value, "threshold": abst_target, "pass": abst_value >= abst_target})
    if blockers:
        return {"status": "BLOCKED", "blockers": blockers, "checks": checks}
    return {"status": "PASS" if all(x["pass"] for x in checks) else "FAIL", "blockers": [], "checks": checks}
