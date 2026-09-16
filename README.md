# RAG Engineering Harness

Framework-agnostic, deterministic-first harness for empirical validation,
diagnosis, controlled optimization, regression testing, and release gating of
Retrieval-Augmented Generation (RAG) systems.

**Version:** 0.4.0

## What this repository does

It evaluates an already-produced RAG run against a frozen gold set. The RAG
stack can use any database, embedding model, reranker, LLM, graph, or framework;
an adapter only needs to export canonical JSONL. The harness itself makes no API
calls and the included smoke test requires no keys, network, embeddings, or paid
models.

Version 0.4 can freeze a corpus manifest, evaluate citations at evidence-locator
level, and recomputes gate metrics from the recorded immutable inputs so an
edited `metrics.json` becomes `BLOCKED`. Risk profiles R0-R3 add deterministic
enterprise authorization, audit, cross-tenant leakage, forbidden-output, and
mandatory-human-approval gates without asking the LLM to police itself.

R2-R3 additionally require an external trust root. A trust anchor approves the
evaluator, gold, risk configuration, corpus manifest, and independent audit log;
its SHA-256 MUST be supplied from outside the evaluated checkout. This prevents
a modified evaluator, substituted gold, or profile downgrade from approving
itself through internally consistent hashes.

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

`INTAKE -> RISK -> AUDIT -> GOLD SET -> BASELINE -> EVALUATE -> ATTACK -> DIAGNOSE -> EXPERIMENT -> REGRESSION -> RELEASE GATE -> HUMAN APPROVAL`

## Risk profiles

| Profile | Intended use | Additional release behavior |
|---|---|---|
| R0 | Public or synthetic | IR, evidence, integrity, operations |
| R1 | Internal non-confidential | Project-specific access and audit controls |
| R2 | Confidential, contractual, personal, or multi-tenant | Authorization, audit completeness, zero critical leakage |
| R3 | Regulated or high-impact | R2 controls, content hashes, evidence citations, mandatory human approval |

Use `profiles/r2-confidential.json` or `profiles/r3-regulated.json` as strict
starting points. Do not weaken them after observing failures.

## External trust root for R2-R3

After independent review, create an approval candidate with
`scripts/create_trust_anchor.py`. Store its printed SHA-256 in a protected CI
secret or deployment policy outside this repository. Supply that digest through
`RAG_HARNESS_TRUST_ANCHOR_SHA256` or `--trust-anchor-sha256` to both `evaluate`
and `gate`, together with the same read-only `--trust-anchor` and independent
`--audit-log`.

Keeping both the anchor and its digest inside a writable evaluated checkout is
not an external root of trust and MUST be reported as BLOCKED for production.

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

R2-R3 runs additionally declare `decision` plus an `audit` object. Enterprise
gold cases declare `expected_action`, `forbidden_doc_ids`, and optional
`forbidden_output_markers`. A forbidden document entering retrieved context is
a critical failure even if it is omitted from the final answer.
Tenant isolation is also derived from `tenant_id` in the corpus manifest and
the independently corroborated audit identity; it does not depend solely on
enumerating forbidden documents in the gold set.

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
- `profiles/`: risk-calibrated R2 and R3 configurations.
- `prompts/`: adapter and controlled-diagnosis prompts.
- `protocols/`: intake, audit, evaluation, diagnosis, security, experiment, and release procedures.

## Methodological boundary

A smoke-test `PASS` proves that the deterministic evaluator and gate behave as
specified on the fixture. It does **not** prove corpus representativeness,
semantic answer correctness, faithfulness, fairness, or production readiness.
Those require project-specific gold data, slice analysis, and—where genuinely
needed—separately validated semantic judges.

## License

MIT. See `LICENSE`.
