# RAG Engineering Harness V0.4.1 — Normative Specification

The keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## Purpose

The harness evaluates canonical outputs from any RAG stack. It does not call a
vector database or LLM. Stack-specific adapters MUST emit the canonical run
contract; the evaluator then computes deterministic metrics and a release gate.

## Lifecycle

`INIT -> AUDIT -> GOLD_SET -> BASELINE -> EVALUATE -> DIAGNOSE -> EXPERIMENT -> REGRESSION -> RELEASE_GATE`

V0.4.1 directly automates configuration validation, deterministic evaluation,
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
10. `gate` MUST recompute decision evidence from the recorded inputs. Editable
    metric values MUST NOT be trusted. A mismatch causes
    `BLOCKED: METRICS_INTEGRITY_FAILURE`.
11. When `require_corpus_manifest` is enabled, the manifest MUST be present,
    hash-stable, and contain every document referenced by the gold set.
12. When `citation_level` is `evidence`, citations MUST identify annotated
    evidence records rather than documents only.
13. Every evaluation MUST declare a risk profile R0-R3. Unknown risk MUST NOT
    be silently interpreted as R0.
14. R2-R3 runs MUST declare a decision and audit evidence. Gold cases MUST
    declare expected actions for authorization tests.
15. Retrieval of a forbidden document or emission of a forbidden marker is a
    critical security failure and MUST NOT be offset by aggregate quality.
16. An R3 automated PASS MUST become BLOCKED pending recorded human approval.
17. R1-R3 MUST use an externally pinned trust-anchor digest. The anchor MUST
    approve evaluator, gold, configuration, corpus manifest, audit log, and
    minimum risk profile.
18. Tenant leakage MUST be detected from trusted corpus and actor metadata even
    when the gold does not enumerate a forbidden document.
19. Self-declared audit fields MUST NOT constitute their own attestation.
20. Query coverage MUST be gated and MUST NOT be inferred from quality on a subset.
21. R1-R3 corpus records MUST identify a tenant or an explicit shared allow-list;
    absent access metadata MUST block closed.
22. Security marker matching MUST normalize Unicode compatibility characters,
    dash variants, formatting characters, case, and whitespace before comparison.
23. External audit corroboration MUST bind query, actor, tenant, policy, decision,
    timestamp, run identifier, and system identifier.
24. Trust-anchor identity is its digest, not its filesystem path. Gate output MUST
    record the anchor digest, expected digest, issuer, approvals, and limitation.

## Metrics

At each configured `K`, the harness computes macro-averaged Hit@K, Recall@K,
Precision@K, MRR@K, and nDCG@K over answerable queries. Unanswerable queries
are evaluated through abstention accuracy and do not enter retrieval denominators.
Binary relevance is derived from
`relevant_doc_ids`; optional `graded_relevance` supplies non-negative relevance
grades for nDCG. It also computes citation precision, citation recall,
abstention accuracy, p95 latency, and mean cost.

Citation precision and recall operate on document IDs or evidence IDs according
to `evaluation.citation_level`. Evidence IDs identify a document locator, but
V0.4.1 still does not claim semantic entailment of the cited text.

## Status

- `PASS`: the declared evaluation contract and all mandatory thresholds and limits pass.
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

V0.4.1 does not claim semantic answer correctness, entailment, chunk-quality,
fairness, or production representativeness. Such evidence requires additional
adapters and validated judge protocols. A V0.4.1 `PASS` means only that the declared
deterministic contract passed on the supplied benchmark.
The evaluated process cannot prove that an anchor digest or runtime is controlled
externally. Therefore automated output MUST NOT claim production authorization;
R3 also remains BLOCKED until a human-approval mechanism exists.
