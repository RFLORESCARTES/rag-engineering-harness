# RAG Engineering Harness — Normative Specification v0.1.0

Keywords MUST, MUST NOT, SHOULD, MAY are normative.

## Mission

Provide reproducible evidence that a RAG system retrieves the right evidence, ranks it appropriately, supplies sufficient context, generates supported answers, cites correctly, abstains when evidence is insufficient, and does so within declared operational constraints.

## Authority hierarchy

1. Human-approved project requirements.
2. This specification.
3. Frozen gold set and regression suite.
4. `rag_harness.yaml` thresholds and policies.
5. Deterministic evaluator outputs.
6. Semantic judge outputs.
7. Agent interpretation.

Lower levels MUST NOT override higher levels.

## Protected evaluation assets

During an evaluation/optimization run, an agent MUST NOT silently modify: gold labels, expected evidence IDs, relevance grades, answerability labels, scoring code, release thresholds, critical-test definitions, or stop conditions. Proposed changes MUST be recorded separately and require explicit human approval before a new baseline is established.

## Required phases

### P0 INIT
Validate configuration, adapter contract, corpus identity/version, run identity, and output paths. Failure to establish corpus or benchmark identity => BLOCKED.

### P1 CORPUS & INGESTION AUDIT
Inspect source inventory, parsing/OCR status, duplicates, document/version metadata, chunk boundaries, provenance, tables/images where relevant, and index coverage. A retrieval failure MUST NOT automatically be attributed to ANN/search parameters.

### P2 GOLD SET
Each case MUST have: unique ID, query, answerable flag, test class, expected evidence IDs or explicit unanswerable ground truth, relevance grades where applicable, and criticality. Gold cases SHOULD include direct, paraphrase, lexical, multi-hop, numeric, table/figure, multimodal, metadata-filter, temporal/version, conflict, hard-negative, ambiguous, and unanswerable cases when applicable.

### P3 BASELINE
Freeze configuration fingerprint and record metrics, latency/cost if available, corpus version, model/index versions, timestamp, and evaluator version.

### P4 EVALUATION
Evaluate layers separately. Retrieval/ranking MUST use deterministic metrics where labels permit. Semantic generation judgments MUST preserve judge/model/version/prompt and raw judgment evidence.

### P5 DIAGNOSIS
Classify observed failures before tuning. Minimum stages: ingestion, chunking, metadata, query processing, retrieval, fusion, filtering, reranking, context selection, generation, citation, abstention, infrastructure.

### P6 CONTROLLED EXPERIMENT
Each experiment MUST state hypothesis, baseline, primary variable, expected effect, result, latency/cost delta when available, decision, and artifacts. Prefer one primary variable per experiment. Multi-variable changes require justification.

### P7 REGRESSION
Any corrected high/critical defect SHOULD become a regression case. Existing regression cases MUST NOT be removed merely to obtain PASS.

### P8 RELEASE GATE
PASS requires every mandatory threshold and zero blockers. FAIL means trustworthy evaluation completed but thresholds failed. BLOCKED means evaluation integrity/completeness is insufficient for a trustworthy verdict.

## Canonical retrieval metrics

For cutoff K:
- Hit@K: whether at least one relevant item occurs in top K.
- Recall@K: retrieved relevant items / all labeled relevant items.
- Precision@K: relevant items in top K / K (or retrieved count when fewer than K are returned).
- Reciprocal Rank@K: reciprocal rank of first relevant item, else zero.
- nDCG@K: DCG normalized by ideal DCG using graded relevance.

Report macro means and per-test-class strata. Critical-case failures MUST remain visible even if macro averages pass.

## Generation/grounding interface

V1 treats semantic generation evaluation as an adapter surface. Recommended dimensions: answer correctness, faithfulness/groundedness, evidence coverage, citation correctness/completeness, and abstention behavior. A semantic score MUST NOT be fabricated when no judge/evaluator ran.

## Abstention matrix

- answerable + correct answer: desired
- answerable + abstain: false abstention
- unanswerable + abstain: desired
- unanswerable + unsupported answer: critical hallucination candidate

## Invariants

- No evidence => no claim of evidence.
- Missing metric => `null`/not measured, never an invented value.
- Benchmark mutation during optimization => BLOCKED unless explicitly approved as a new benchmark version.
- Evaluator/scoring mutation during comparison => BLOCKED unless both baseline and candidate are rerun under the new evaluator.
- A critical hallucination or provenance integrity violation MAY be configured as an immediate blocker.
- Optimization MUST NOT begin solely from aggregate score; failures must be localized first.

## Reproducibility record

Every run SHOULD preserve: git commit, config hash, corpus/index version, gold-set hash, adapter version, model identifiers, timestamps, environment information, raw retrieval results, calculated metrics, diagnoses, experiments, and gate verdict.
