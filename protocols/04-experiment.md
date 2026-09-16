# Controlled experiment protocol

Freeze the baseline commit, benchmark, evaluator, and thresholds. Register one
primary variable, hypothesis, predicted metric movement, cost ceiling, and stop
condition. Run baseline and candidate on identical query sets. Record the result
using `schemas/experiment.schema.json`. Reject changes that improve the target
metric while violating a mandatory gate or integrity invariant.
