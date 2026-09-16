---
name: rag-engineer
description: Evaluate, diagnose, and gate a RAG system using this repository's deterministic contracts. Use when given canonical gold/run data or when adapting a RAG stack to the harness; do not use it to claim semantic or production validity beyond the evidence measured.
---

# RAG Engineer

Use the repository as the authority. Read `RAG_HARNESS_SPEC.md` before operating
the harness and read only the protocol relevant to the current phase.

Preserve the evaluation contract. Never edit gold data, thresholds, fixtures,
evaluator code, or stop conditions to obtain `PASS`. Convert stack-specific
outputs to `schemas/run.schema.json`; do not embed provider behavior in the
evaluator.

For an evaluation:

1. Validate configuration.
2. Evaluate the frozen gold and run files.
3. Execute the release gate.
4. Report technical execution, procedural validity, and methodological limits
   separately.
5. Preserve `PASS`, `FAIL`, or `BLOCKED` exactly. A blocker takes precedence over
   averages and a smoke-test PASS does not establish production readiness.

Use `protocols/03-diagnosis.md` before proposing changes. For optimization, read
`protocols/04-experiment.md` and change one primary variable at a time. For
release decisions, read `protocols/05-release.md`.
