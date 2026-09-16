# RAG Engineering Harness

Framework-agnostic, deterministic-first harness for empirical validation, diagnosis, controlled optimization, regression testing, and release gating of Retrieval-Augmented Generation (RAG) systems.

**Version:** 0.1.0 (V1 foundation)

## Design principles

1. **Diagnose before optimize.** No tuning before the failing layer is identified with evidence.
2. **Deterministic-first.** Compute retrieval/ranking/gating metrics in code; use LLM judges only for irreducibly semantic judgments.
3. **Immutable evaluation contract.** Agents must not silently edit the gold set, thresholds, scoring code, or stop conditions to obtain a pass.
4. **Layered evaluation.** Audit ingestion, retrieval, ranking, context, generation, citations, abstention, latency/cost, and regression separately.
5. **Controlled experiments.** Change one primary variable at a time, compare against a frozen baseline, and record the result.
6. **Failure becomes memory.** Every corrected production-relevant failure becomes a regression test.
7. **Provider agnostic.** The harness contract is independent of vector database, embedding model, reranker, LLM, orchestration framework, and graph implementation.

## Lifecycle

`INIT -> AUDIT -> GOLD SET -> BASELINE -> EVALUATE -> DIAGNOSE -> EXPERIMENT -> REGRESSION -> RELEASE GATE`

## Quick start

```bash
python -m pip install -e .
rag-harness validate-config rag_harness.yaml
rag-harness evaluate --gold tests/fixtures/gold.jsonl --run tests/fixtures/run.jsonl --out reports/latest
rag-harness gate --metrics reports/latest/metrics.json --config rag_harness.yaml
```

The included fixture intentionally contains a small deterministic benchmark so the evaluator and gate can be smoke-tested without API keys, embeddings, or paid models.

## Core files

- `RAG_HARNESS_SPEC.md`: normative contract and stop conditions.
- `skills/rag-engineer/SKILL.md`: portable operating instructions for an LLM/agent.
- `rag_harness.yaml`: project configuration and release thresholds.
- `schemas/`: machine-readable contracts.
- `src/rag_harness/`: deterministic evaluator, gate, validation, and CLI.
- `tests/fixtures/`: minimal executable benchmark.
- `protocols/`: operational procedures for corpus audit, evaluation, diagnosis, experiments, and release.

## Evaluation model

Retrieval metrics include Hit@K, Recall@K, Precision@K, MRR@K, and nDCG@K. This follows established IR practice; BEIR exposes nDCG, MAP, Recall, Precision and custom MRR evaluation. Generation-side semantic metrics are deliberately adapter-based rather than hard-wired to one judge framework.

## Status semantics

- **PASS**: every mandatory gate passes and no critical invariant is violated.
- **FAIL**: evaluation completed, but one or more quality thresholds fail.
- **BLOCKED**: trustworthy evaluation cannot be completed (for example invalid gold set, missing provenance, benchmark mutation, missing required evidence, or evaluator integrity failure).

A high average score never overrides a critical blocker.

## Scope of V1

V1 supplies the portable contract, deterministic IR evaluator, configuration validation, release gate, schemas, test taxonomy, experiment ledger contract, generic adapter contract, and smoke-test fixtures. Live connectors to individual RAG stacks are intentionally adapters: they should transform stack-specific outputs into the canonical run schema rather than changing the evaluator.

## License

MIT. See `LICENSE`.
