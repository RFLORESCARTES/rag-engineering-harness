from __future__ import annotations

import json
import os
from pathlib import Path

from .errors import BlockedError
from .integrity import evaluator_hash, sha256_file


RISK_ORDER = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}


def verify_trust_anchor(
    anchor_path: Path | None,
    expected_anchor_sha256: str | None,
    gold_path: Path,
    config_path: Path,
    corpus_manifest: Path | None,
    audit_log: Path | None,
    risk_profile: str,
) -> None:
    if anchor_path is None:
        raise BlockedError("MISSING_TRUST_ANCHOR", "risk profile requires an external trust anchor")
    expected = expected_anchor_sha256 or os.environ.get("RAG_HARNESS_TRUST_ANCHOR_SHA256")
    if not expected:
        raise BlockedError("MISSING_TRUST_ROOT", "supply --trust-anchor-sha256 or RAG_HARNESS_TRUST_ANCHOR_SHA256 from outside the evaluated repository")
    if sha256_file(anchor_path) != expected:
        raise BlockedError("TRUST_ANCHOR_MISMATCH", "trust anchor does not match the externally supplied digest")
    try:
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BlockedError("INVALID_TRUST_ANCHOR", str(exc)) from exc
    approved = anchor.get("approved", {})
    checks = {
        "evaluator_sha256": evaluator_hash(),
        "gold_sha256": sha256_file(gold_path),
        "config_sha256": sha256_file(config_path),
    }
    if corpus_manifest is not None:
        checks["corpus_manifest_sha256"] = sha256_file(corpus_manifest)
    if audit_log is not None:
        checks["audit_log_sha256"] = sha256_file(audit_log)
    for name, observed in checks.items():
        if approved.get(name) != observed:
            raise BlockedError("UNAPPROVED_EVALUATION_CONTRACT", f"{name} is not approved by the external trust anchor")
    minimum = anchor.get("minimum_risk_profile")
    if minimum not in RISK_ORDER or RISK_ORDER[risk_profile] < RISK_ORDER[minimum]:
        raise BlockedError("RISK_PROFILE_DOWNGRADE", f"configured {risk_profile} is below approved minimum {minimum}")
