from __future__ import annotations
import math


def _rel(item_id: str, grades: dict[str, float]) -> float:
    return float(grades.get(item_id, 0.0))


def metrics_at_k(retrieved: list[str], grades: dict[str, float], k: int) -> dict[str, float]:
    top = retrieved[:k]
    relevant = {x for x, g in grades.items() if g > 0}
    hits = [x for x in top if x in relevant]
    hit = 1.0 if hits else 0.0
    recall = len(set(hits)) / len(relevant) if relevant else 0.0
    precision = len(hits) / len(top) if top else 0.0
    rr = 0.0
    for rank, item in enumerate(top, 1):
        if item in relevant:
            rr = 1.0 / rank
            break
    dcg = sum((2 ** _rel(item, grades) - 1) / math.log2(rank + 1) for rank, item in enumerate(top, 1))
    ideal = sorted((float(g) for g in grades.values() if g > 0), reverse=True)[:k]
    idcg = sum((2 ** g - 1) / math.log2(rank + 1) for rank, g in enumerate(ideal, 1))
    ndcg = dcg / idcg if idcg else 0.0
    return {"hit_rate": hit, "recall": recall, "precision": precision, "mrr": rr, "ndcg": ndcg}


def macro(rows: list[dict[str, float]]) -> dict[str, float]:
    if not rows:
        return {}
    return {key: sum(r[key] for r in rows) / len(rows) for key in rows[0]}
