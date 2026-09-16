from rag_harness.metrics import metrics_at_k
from rag_harness.gate import release_gate


def test_metrics_perfect_first_hit():
    m = metrics_at_k(["a", "x"], {"a": 3}, 2)
    assert m["hit_rate"] == 1.0
    assert m["recall"] == 1.0
    assert m["mrr"] == 1.0
    assert m["ndcg"] == 1.0


def test_gate_blocks_missing_cases():
    metrics = {"integrity": {"missing_run_ids": ["Q1"]}, "aggregate": {}, "abstention": {}}
    config = {"primary_cutoff": 10, "release_gate": {"retrieval": {}, "abstention": {}}}
    assert release_gate(metrics, config)["status"] == "BLOCKED"
