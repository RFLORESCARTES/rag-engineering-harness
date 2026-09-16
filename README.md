# RAG Engineering Harness

Framework-agnostic, deterministic-first harness for empirical validation,
diagnosis, controlled optimization, regression testing, and release gating of
Retrieval-Augmented Generation (RAG) systems.

**Version:** 0.1.0 (V1 foundation)

## What this repository does

It evaluates an already-produced RAG run against a frozen gold set. The RAG
stack can use any database, embedding model, reranker, LLM, graph, or framework;
an adapter only needs to export canonical JSONL. The harness itself makes no API
calls and the included smoke test requires no keys, network, embeddings, or paid
models.

## Design principles

1. **Diagnose before optimize.** Do not tune before locating the failing layer.
2. **Deterministic-first.** Compute measurable IR and gate evidence in code.
3. **Immutable evaluation contract.** Never edit gold data, thresholds, scoring,
   fixtures, or stop conditions to manufacture a pass.
4. **Layered evaluation.** Separate ingestion, retrieval, ranking, context,
   generation, citations, abstention, latency/cost, and regression.
5. **Controlled experiments.** Change one primary variable at a time.
6. **Failure becomes memory.** Add corrected real failures as regressions.
7. **Provider agnostic.** Normalize provider output; do not change the evaluator.

## Lifecycle

`INIT -> AUDIT -> GOLD SET -> BASELINE -> EVALUATE -> DIAGNOSE -> EXPERIMENT -> REGRESSION -> RELEASE GATE`

## Quick start

Python 3.10 or newer is required. From a clean checkout:

```bash
python -m pip install -e .
rag-harness validate-config rag_harness.yaml
rag-harness evaluate \
  --gold tests/fixtures/gold.jsonl \
  --run tests/fixtures/run.jsonl \
  --out reports/latest
rag-harness gate \
  --metrics reports/latest/metrics.json \
  --config rag_harness.yaml
```

The final command writes `reports/latest/gate.json` and exits `0` for the
included passing fixture. Run the test suite with:

```bash
python -m unittest discover -s tests -v
```

To confirm that the gate distinguishes poor quality from broken evidence:

```bash
rag-harness evaluate \
  --gold tests/fixtures/gold.jsonl \
  --run tests/fixtures/run_fail.jsonl \
  --out reports/failing
rag-harness gate \
  --metrics reports/failing/metrics.json \
  --config rag_harness.yaml
```

That gate is expected to return `FAIL` with exit code `1`, not `BLOCKED`.

## Canonical adapter output

Each line of a run is one JSON object:

```json
{
  "query_id": "q1",
  "retrieved": [{"doc_id": "doc-7", "rank": 1, "score": 0.91}],
  "answer": "Example answer",
  "citations": ["doc-7"],
  "abstained": false,
  "latency_ms": 125,
  "cost_usd": 0.001,
  "provenance": {
    "system": "my-rag",
    "run_id": "baseline-001",
    "created_at": "2026-09-16T00:00:00Z"
  }
}
```

See `schemas/run.schema.json` for the machine-readable contract.

## Metrics and integrity

The evaluator computes Hit@K, Recall@K, Precision@K, MRR@K, nDCG@K, citation
precision/recall, abstention accuracy, p95 latency, and mean cost. It records
SHA-256 hashes of the gold set, run, configuration, and evaluator code before
and after evaluation. The gate rechecks those hashes. Mutation produces
`BLOCKED: EVALUATION_CONTRACT_MUTATED` instead of a potentially false result.

The configuration file is named `.yaml` but deliberately uses JSON-compatible
YAML, allowing offline parsing with Python's standard library and no runtime
dependencies.

## Status and exit codes

| Verdict | Meaning | Exit code |
|---|---|---:|
| `PASS` | Trustworthy evaluation and every mandatory gate passed | 0 |
| `FAIL` | Trustworthy evaluation completed, but a quality gate failed | 1 |
| `BLOCKED` | Trustworthy evaluation could not be completed | 2 |

A high average never overrides a critical blocker.

## Repository map

- `RAG_HARNESS_SPEC.md`: normative contract, invariants, and boundaries.
- `skills/rag-engineer/SKILL.md`: portable agent operating instructions.
- `rag_harness.yaml`: thresholds, limits, and integrity policy.
- `schemas/`: canonical gold, run, metrics, and experiment contracts.
- `src/rag_harness/`: evaluator, integrity verifier, gate, and CLI.
- `tests/fixtures/`: passing and failing deterministic benchmarks.
- `protocols/`: audit, evaluation, diagnosis, experiment, and release procedures.

## Methodological boundary

A smoke-test `PASS` proves that the deterministic evaluator and gate behave as
specified on the fixture. It does **not** prove corpus representativeness,
semantic answer correctness, faithfulness, fairness, or production readiness.
Those require project-specific gold data, slice analysis, and—where genuinely
needed—separately validated semantic judges.

## License

MIT. See `LICENSE`.
