# Regression and release protocol

Convert corrected production-relevant failures into permanent regression cases.
Before release, rerun unit tests plus the frozen benchmark from a clean checkout.
Release only on `PASS`, with no blocker and an unchanged evaluation contract.
`FAIL` requires quality work; `BLOCKED` requires restoring trustworthy evidence.
A fixture PASS is a smoke test, not evidence of production readiness.
