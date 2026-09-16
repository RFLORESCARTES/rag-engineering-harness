---
name: rag-engineer
description: Evaluate, diagnose, harden, and release-gate RAG systems with immutable deterministic contracts, evidence-level citations, risk profiles R0-R3, and enterprise authorization/security tests. Use for corpus audit, adapter design, benchmark execution, controlled optimization, regression, or production readiness. Never infer production safety from retrieval quality alone.
---

# RAG Engineer

Treat this repository as the normative authority. Read `RAG_HARNESS_SPEC.md`,
then `protocols/00-intake-risk.md`, and only the protocol for the active phase.

## Non-negotiable invariants

- Never edit gold, thresholds, attack fixtures, evaluator code, or stop
  conditions to obtain PASS.
- Never treat document relevance as proof of evidence support, authorization,
  privacy, or safety.
- Never let an LLM grant access, infer roles, change tenant, or waive a blocker.
- Never expose forbidden document existence in a denial response.
- Preserve PASS, FAIL, BLOCKED, and NOT_EVALUATED exactly.
- A critical security event overrides every average metric.

## Operating loop

1. **INTAKE:** identify corpus, RAG interface, intended users, consequences,
   external providers, and required outputs.
2. **CLASSIFY:** assign R0-R3. If evidence is insufficient, choose the more
   restrictive plausible profile and record the uncertainty.
3. **FREEZE:** hash configuration, corpus manifest, gold, attack set, run, and
   evaluator. Never tune on the final test set.
4. **ADAPT:** normalize system output to `schemas/run.schema.json`. Keep provider
   behavior in adapters, never in the evaluator.
5. **BASELINE:** run a cheap deterministic baseline and an oracle evaluator
   self-test. Label oracle output clearly; it is not a RAG result.
6. **EVALUATE:** execute configuration validation, evaluation, then gate.
7. **ATTACK:** for R2-R3 run cross-tenant, forbidden-output, authorization,
   stored-injection, stale-policy, and audit-completeness cases.
8. **DIAGNOSE:** localize the first failing layer. Separate observed evidence,
   inference, and uncertainty.
9. **EXPERIMENT:** register one primary variable and predicted movement. Reuse
   identical frozen inputs. Reject improvements that violate another gate.
10. **REGRESS:** convert corrected production-relevant failures into permanent tests.
11. **RELEASE:** rerun from a clean checkout. R3 always requires recorded human
    approval and cannot auto-release.

## Required call order

```bash
rag-harness validate-config PROFILE.json
rag-harness evaluate --gold GOLD.jsonl --run RUN.jsonl \
  --config PROFILE.json --corpus-manifest CORPUS.jsonl \
  --audit-log AUDIT.jsonl --trust-anchor APPROVED.json --out REPORT_DIR
rag-harness gate --metrics REPORT_DIR/metrics.json \
  --config PROFILE.json --audit-log AUDIT.jsonl \
  --trust-anchor APPROVED.json --out REPORT_DIR/gate.json
```

Do not call `gate` on hand-authored metrics. The gate recomputes decision
evidence and blocks any mismatch.
For R1-R3, require the trust-anchor SHA-256 from a protected source outside the
evaluated checkout. An anchor and digest both writable by the evaluated agent
do not establish trust.
Treat incomplete query coverage and missing tenant/access metadata as gate
failures or blockers, never as permission to score only the favorable subset.
Report the complete `gate.json.trust` provenance and never reinterpret its
`production_authorized: false` field as a release approval.

## Fail fast and report

Stop as BLOCKED before optimization when required evidence, access metadata,
content hashes, provenance, query completeness, evaluator integrity, or audit
records are missing. Stop as FAIL on an observed quality or security violation.

Report technical execution, retrieval/evidence, measured answer quality,
authorization, privacy/security, reproducibility, methodological validity,
production decision, limitations, and every NOT_EVALUATED dimension separately.
A fixture or oracle PASS does not establish production readiness.
