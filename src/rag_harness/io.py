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
    ks = ev.get("k_values")
    if not isinstance(ks, list) or not ks or any(not isinstance(k, int) or k < 1 for k in ks):
        raise HarnessError("evaluation.k_values must contain positive integers")
    if len(set(ks)) != len(ks):
        raise HarnessError("evaluation.k_values must be unique")
    if ev.get("primary_k") not in ks:
        raise HarnessError("evaluation.primary_k must occur in k_values")
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
