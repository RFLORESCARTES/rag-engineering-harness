# RAG Engineering Harness V1 — Normative Specification

The keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## Purpose

The harness evaluates canonical outputs from any RAG stack. It does not call a
vector database or LLM. Stack-specific adapters MUST emit the canonical run
contract; the evaluator then computes deterministic metrics and a release gate.

## Lifecycle

`INIT -> AUDIT -> GOLD_SET -> BASELINE -> EVALUATE -> DIAGNOSE -> EXPERIMENT -> REGRESSION -> RELEASE_GATE`

V1 directly automates configuration validation, deterministic evaluation,
contract-integrity recording, and release gating. The remaining phases have
operational protocols in `protocols/`.

## Evaluation contract

1. Query identifiers MUST be unique in both gold and run files.
2. Every gold query MUST have a run result when completeness is required.
3. Unknown run query identifiers MUST cause `BLOCKED`.
4. Every answerable gold query MUST declare at least one relevant document.
5. Ranks MUST be positive, unique, and contiguous from 1 per query.
6. Document identifiers MUST be unique within a retrieved list.
7. `gold`, `run`, configuration, and evaluator code are hashed before and after
   evaluation. A mutation causes `BLOCKED`.
8. `gate` MUST recompute the hashes of recorded paths. A mismatch causes
   `BLOCKED: EVALUATION_CONTRACT_MUTATED`.
9. Agents MUST NOT change gold data, thresholds, evaluator code, fixtures, or
   stop conditions to obtain a favorable outcome.

## Metrics

At each configured `K`, the harness computes macro-averaged Hit@K, Recall@K,
Precision@K, MRR@K, and nDCG@K over answerable queries. Unanswerable queries
are evaluated through abstention accuracy and do not enter retrieval denominators.
Binary relevance is derived from
`relevant_doc_ids`; optional `graded_relevance` supplies non-negative relevance
grades for nDCG. It also computes citation precision, citation recall,
abstention accuracy, p95 latency, and mean cost.

Citation precision is the proportion of cited document IDs that are relevant.
Citation recall is the proportion of relevant IDs cited. These are evidence-ID
metrics, not semantic faithfulness judgments.

## Status

- `PASS`: evaluation is trustworthy and all mandatory thresholds and limits pass.
- `FAIL`: evaluation is trustworthy but at least one gate fails.
- `BLOCKED`: trustworthy evaluation cannot be completed.

Quality averages MUST NOT override a blocker. Invalid inputs, missing mandatory
evidence, non-finite numbers, contract mutation, or evaluator-integrity failure
are blockers.

## Exit codes

- `0`: command succeeded; gate verdict is `PASS`.
- `1`: gate verdict is `FAIL` or ordinary command error.
- `2`: verdict is `BLOCKED`.

## Known boundary

V1 does not claim semantic answer correctness, entailment, chunk-quality,
fairness, or production representativeness. Such evidence requires additional
adapters and validated judge protocols. A V1 `PASS` means only that the declared
deterministic contract passed on the supplied benchmark.
