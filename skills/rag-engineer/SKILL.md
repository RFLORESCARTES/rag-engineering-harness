# RAG Engineer Skill

Purpose: operate this harness using empirical evidence and reproducible tests.

## Startup
Read `RAG_HARNESS_SPEC.md`, then `rag_harness.yaml`. Identify the target RAG, corpus/index version, adapter, gold set, constraints, and requested mode.

## Modes
`AUDIT_ONLY`, `EVALUATE_ONLY`, `DIAGNOSE_ONLY`, `OPTIMIZE`, `RELEASE_GATE`, `FULL`.

## Rules
- Preserve the approved benchmark, thresholds, evaluator logic, and stop conditions during a comparison.
- Never claim a metric was measured unless an evaluator produced it.
- Check upstream ingestion and indexing causes before tuning ANN parameters.
- Separate measurements, hypotheses, interpretations, and recommendations.
- Prefer deterministic checks to LLM judgment.
- Preserve raw evidence and experiment history.
- If required evidence is missing, return `BLOCKED` with the missing artifact rather than guessing.

## Diagnosis order
`source -> parse/OCR -> chunk -> metadata/provenance -> index coverage -> query processing -> retrieval -> fusion/filter -> rerank -> context packing -> generation -> citation -> abstention`.

## Optimization loop
Reproduce failure -> localize layer -> state falsifiable hypothesis -> select one primary intervention -> freeze baseline -> execute candidate -> compare quality and latency/cost -> accept/reject -> add fixed high/critical failure to regression -> rerun gate.

## Human approval points
Request approval before changing gold truth, lowering thresholds, removing regression cases, changing criticality, changing evaluator semantics, or establishing a new benchmark version.

## Required report
Run identity; fingerprints; baseline; metrics by layer/test class; critical failures; failure taxonomy; experiments; regressions; release gate; unmeasured dimensions; exact next action.

Machine-readable artifacts are authoritative. Narrative summaries must remain consistent with them, and averages must not conceal critical failures.
