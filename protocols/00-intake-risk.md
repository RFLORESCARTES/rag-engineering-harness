# Intake and risk-classification protocol

Record intended use, users, corpus owner, information classes, tenants,
jurisdictions, external processors, consequences of wrong answers, and human
oversight before changing configuration or data.

Assign exactly one profile: R0 public/synthetic; R1 internal non-confidential;
R2 confidential, contractual, personal, financial, or multi-tenant; R3
regulated or high-impact, including health, biometric, legal, or
rights-affecting use.

If required facts are unknown, do not assume R0. Record uncertainty and use the
most restrictive plausible profile. A downgrade requires reviewable evidence.
Produce `risk_assessment.json` before evaluation.
