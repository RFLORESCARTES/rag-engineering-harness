from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .errors import BlockedError, HarnessError
from .evaluator import evaluate
from .gate import gate
from .io import dump_json, load_config


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="rag-harness")
    sub = root.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-config")
    validate.add_argument("config", type=Path)
    ev = sub.add_parser("evaluate")
    ev.add_argument("--gold", required=True, type=Path)
    ev.add_argument("--run", required=True, type=Path)
    ev.add_argument("--config", type=Path, default=Path("rag_harness.yaml"))
    ev.add_argument("--corpus-manifest", type=Path)
    ev.add_argument("--trust-anchor", type=Path)
    ev.add_argument("--trust-anchor-sha256")
    ev.add_argument("--audit-log", type=Path)
    ev.add_argument("--out", required=True, type=Path)
    gt = sub.add_parser("gate")
    gt.add_argument("--metrics", required=True, type=Path)
    gt.add_argument("--config", required=True, type=Path)
    gt.add_argument("--out", type=Path)
    gt.add_argument("--trust-anchor", type=Path)
    gt.add_argument("--trust-anchor-sha256")
    gt.add_argument("--audit-log", type=Path)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "validate-config":
            load_config(args.config)
            print(json.dumps({"status": "PASS", "config": str(args.config)}))
            return 0
        if args.command == "evaluate":
            result = evaluate(args.gold, args.run, args.config, args.out, args.corpus_manifest, args.trust_anchor, args.trust_anchor_sha256, args.audit_log)
            print(json.dumps({"status": "EVALUATED", "queries": result["query_count"], "metrics": str(args.out / "metrics.json")}))
            return 0
        metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
        output = args.out or args.metrics.with_name("gate.json")
        result = gate(metrics, args.config, output, args.trust_anchor, args.trust_anchor_sha256, args.audit_log)
        print(json.dumps(result))
        return 0 if result["verdict"] == "PASS" else (2 if result["verdict"] == "BLOCKED" else 1)
    except BlockedError as exc:
        payload = {"verdict": "BLOCKED", "code": exc.code, "message": str(exc)}
        if getattr(args, "out", None):
            path = args.out if args.command == "gate" else args.out / "blocked.json"
            dump_json(path, payload)
        print(json.dumps(payload), file=sys.stderr)
        return 2
    except (HarnessError, OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
