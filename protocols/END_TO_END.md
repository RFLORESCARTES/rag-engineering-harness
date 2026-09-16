# End-to-End Protocol

## 0. Intake
Declare target system, corpus, environment, constraints, adapter, benchmark, and mode. Hash/version mutable assets.

## 1. Corpus audit
Inventory source documents and modalities; detect parse/OCR failures, empty/near-empty sources, duplicates, stale/superseded versions, missing provenance, metadata inconsistencies, table/image loss, and index coverage gaps. Record findings before retrieval tuning.

## 2. Benchmark construction/review
Stratify cases across applicable classes: direct, paraphrase, lexical, multi-hop, numeric, table/figure, multimodal, metadata, temporal/version, conflict, hard negative, ambiguous, unanswerable, regression. Human-review critical gold labels.

## 3. Baseline
Freeze system/config/corpus/gold/evaluator versions. Execute every gold case through the target RAG adapter. Persist canonical `run.jsonl`, raw responses, latency/cost when available, and errors.

## 4. Deterministic evaluation
Compute retrieval/ranking metrics at configured K values. Report aggregate and per-case values. Evaluate metadata/version rules with explicit assertions when present. Do not replace missing measurements with estimates.

## 5. Generation evaluation
If answers are produced, run configured semantic evaluators for correctness/faithfulness and deterministic citation/provenance checks where possible. Record judge identity/version. Test abstention on unanswerable cases.

## 6. Diagnose
For each material failure create a record with: stage, failure class, severity, observed evidence, plausible causes, discriminating test, and next experiment. Diagnose earliest plausible causal layer first.

## 7. Controlled optimization
Run one-primary-variable experiments. Candidate changes may include parsing, chunking, metadata, query transformation, dense/sparse retrieval, fusion (e.g. RRF), filters, ANN search settings, reranking, context packing, generation policy, or abstention threshold. Do not assume hybrid retrieval or a reranker is always superior: demonstrate the delta on the benchmark.

## 8. Regression
Promote corrected high/critical defects into `tests/regression/`. Rerun baseline-relevant and regression suites after accepted changes.

## 9. Release gate
Run configured gates. Emit PASS, FAIL, or BLOCKED plus machine-readable checks. Never convert BLOCKED into PASS through narrative judgment.

## 10. Deliverables
Minimum: corpus audit, benchmark manifest, canonical run, metrics JSON, failure register, experiment ledger, regression results, release verdict, and concise human report.
