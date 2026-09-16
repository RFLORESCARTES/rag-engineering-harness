from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path
from .metrics import metrics_at_k, macro


def load_jsonl(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def evaluate(gold_path: str, run_path: str, cutoffs: list[int]) -> dict:
    gold = {r["id"]: r for r in load_jsonl(gold_path)}
    run = {r["id"]: r for r in load_jsonl(run_path)}
    missing = sorted(set(gold) - set(run))
    extra = sorted(set(run) - set(gold))
    per_case = []
    strata = defaultdict(list)

    for case_id, g in gold.items():
        r = run.get(case_id, {"retrieved": [], "abstained": None})
        grades = g.get("relevance", {})
        row = {"id": case_id, "class": g["class"], "criticality": g.get("criticality", "normal"), "answerable": g["answerable"], "metrics": {}}
        if g["answerable"]:
            for k in cutoffs:
                row["metrics"][str(k)] = metrics_at_k(r.get("retrieved", []), grades, k)
        row["abstained"] = r.get("abstained")
        per_case.append(row)
        strata[g["class"]].append(row)

    aggregate = {}
    for k in cutoffs:
        vals = [x["metrics"][str(k)] for x in per_case if x["answerable"]]
        aggregate[str(k)] = macro(vals)

    unanswerable = [x for x in per_case if not x["answerable"]]
    measured_unanswerable = [x for x in unanswerable if x["abstained"] is not None]
    safe = sum(1 for x in measured_unanswerable if x["abstained"] is True)
    abstention = {
        "unanswerable_cases": len(unanswerable),
        "measured": len(measured_unanswerable),
        "unanswerable_safe_rate": safe / len(measured_unanswerable) if measured_unanswerable else None,
    }
    return {"aggregate": aggregate, "abstention": abstention, "per_case": per_case, "integrity": {"missing_run_ids": missing, "extra_run_ids": extra}}


def write_report(result: dict, out_dir: str) -> None:
    p = Path(out_dir); p.mkdir(parents=True, exist_ok=True)
    (p / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
