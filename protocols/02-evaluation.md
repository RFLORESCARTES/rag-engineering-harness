# Evaluation protocol

1. Freeze a representative gold set and record its provenance.
2. Export stack output to `schemas/run.schema.json` without changing the gold set.
3. Run `validate-config`, `evaluate`, and `gate` in that order.
4. Preserve `metrics.json`, `gate.json`, source commit, environment, and logs.
5. Treat exit code 2 as `BLOCKED`; do not reinterpret it as a quality failure.
6. Report deterministic evidence separately from any semantic judge evidence.
