from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .errors import BlockedError, HarnessError


def load_config(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HarnessError(f"configuration not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise HarnessError(
            f"configuration must use JSON-compatible YAML: {exc}"
        ) from exc
    validate_config(data)
    return data


def validate_config(config: dict[str, Any]) -> None:
    required = {"version", "evaluation", "thresholds", "limits", "integrity"}
    missing = sorted(required - config.keys())
    if missing:
        raise HarnessError(f"missing configuration sections: {missing}")
    ev = config["evaluation"]
    risk = config.get("risk_profile", "R0")
    if risk not in {"R0", "R1", "R2", "R3"}:
        raise HarnessError("risk_profile must be R0, R1, R2, or R3")
    ks = ev.get("k_values")
    if not isinstance(ks, list) or not ks or any(not isinstance(k, int) or k < 1 for k in ks):
        raise HarnessError("evaluation.k_values must contain positive integers")
    if len(set(ks)) != len(ks):
        raise HarnessError("evaluation.k_values must be unique")
    if ev.get("primary_k") not in ks:
        raise HarnessError("evaluation.primary_k must occur in k_values")
    if ev.get("citation_level", "document") not in {"document", "evidence"}:
        raise HarnessError("evaluation.citation_level must be document or evidence")
    coverage = ev.get("minimum_query_coverage", 1.0)
    if not isinstance(coverage, (int, float)) or isinstance(coverage, bool) or not math.isfinite(coverage) or not 0 <= coverage <= 1:
        raise HarnessError("evaluation.minimum_query_coverage must be within [0, 1]")
    for flag in ("require_complete_query_set", "require_provenance", "require_evidence", "require_corpus_manifest", "require_content_hashes"):
        if flag in ev and not isinstance(ev[flag], bool):
            raise HarnessError(f"evaluation.{flag} must be boolean")
    for name, value in config["thresholds"].items():
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            raise HarnessError(f"threshold {name} must be finite")
        if not 0 <= value <= 1:
            raise HarnessError(f"threshold {name} must be within [0, 1]")
    for name, value in config["limits"].items():
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
            raise HarnessError(f"limit {name} must be finite and non-negative")
    if config["integrity"].get("algorithm") != "sha256":
        raise HarnessError("V1 supports only sha256 integrity hashes")
    enterprise = config.get("enterprise", {})
    if risk in {"R2", "R3"}:
        required_enterprise = {"authorization_accuracy", "audit_completeness", "max_critical_security_failures"}
        missing_enterprise = sorted(required_enterprise - enterprise.keys())
        if missing_enterprise:
            raise HarnessError(f"risk profile {risk} requires enterprise controls: {missing_enterprise}")
    for name in ("authorization_accuracy", "audit_completeness"):
        if name in enterprise and (not isinstance(enterprise[name], (int, float)) or isinstance(enterprise[name], bool) or not 0 <= enterprise[name] <= 1):
            raise HarnessError(f"enterprise.{name} must be within [0, 1]")
    if "max_critical_security_failures" in enterprise and (not isinstance(enterprise["max_critical_security_failures"], int) or enterprise["max_critical_security_failures"] < 0):
        raise HarnessError("enterprise.max_critical_security_failures must be a non-negative integer")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise BlockedError("MISSING_EVIDENCE", f"input not found: {path}") from exc
    for line_no, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BlockedError("INVALID_JSONL", f"{path}:{line_no}: {exc}") from exc
        if not isinstance(row, dict):
            raise BlockedError("INVALID_SCHEMA", f"{path}:{line_no}: expected object")
        rows.append(row)
    if not rows:
        raise BlockedError("MISSING_EVIDENCE", f"input has no records: {path}")
    return rows


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
