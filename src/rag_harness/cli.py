from __future__ import annotations
import argparse, json
from pathlib import Path
import yaml
from .evaluator import evaluate, write_report
from .gate import release_gate


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    p = argparse.ArgumentParser(prog="rag-harness")
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate-config"); v.add_argument("config")
    e = sub.add_parser("evaluate"); e.add_argument("--gold", required=True); e.add_argument("--run", required=True); e.add_argument("--out", required=True); e.add_argument("--config", default="rag_harness.yaml")
    g = sub.add_parser("gate"); g.add_argument("--metrics", required=True); g.add_argument("--config", default="rag_harness.yaml")
    args = p.parse_args()

    if args.cmd == "validate-config":
        c = load_yaml(args.config)
        required = ["version", "cutoffs", "primary_cutoff", "release_gate", "policies"]
        missing = [x for x in required if x not in c]
        print(json.dumps({"status": "PASS" if not missing else "BLOCKED", "missing": missing}, indent=2))
        raise SystemExit(0 if not missing else 2)
    if args.cmd == "evaluate":
        c = load_yaml(args.config)
        result = evaluate(args.gold, args.run, c["cutoffs"])
        write_report(result, args.out)
        print(json.dumps(result["aggregate"], indent=2))
        return
    if args.cmd == "gate":
        c = load_yaml(args.config)
        metrics = json.loads(Path(args.metrics).read_text(encoding="utf-8"))
        verdict = release_gate(metrics, c)
        print(json.dumps(verdict, indent=2))
        raise SystemExit(0 if verdict["status"] == "PASS" else 2)

if __name__ == "__main__":
    main()
