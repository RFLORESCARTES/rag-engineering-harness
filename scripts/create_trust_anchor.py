"""Create an approval candidate; store its printed digest outside the repository."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rag_harness.integrity import evaluator_hash, sha256_file


parser = argparse.ArgumentParser()
parser.add_argument("--gold", required=True, type=Path)
parser.add_argument("--config", required=True, type=Path)
parser.add_argument("--corpus-manifest", required=True, type=Path)
parser.add_argument("--audit-log", type=Path)
parser.add_argument("--minimum-risk-profile", required=True, choices=("R0", "R1", "R2", "R3"))
parser.add_argument("--issued-by", required=True)
parser.add_argument("--out", required=True, type=Path)
args = parser.parse_args()

approved = {
    "evaluator_sha256": evaluator_hash(),
    "gold_sha256": sha256_file(args.gold),
    "config_sha256": sha256_file(args.config),
    "corpus_manifest_sha256": sha256_file(args.corpus_manifest),
}
if args.audit_log:
    approved["audit_log_sha256"] = sha256_file(args.audit_log)

anchor = {
    "schema_version": "1.0",
    "minimum_risk_profile": args.minimum_risk_profile,
    "issued_by": args.issued_by,
    "approved": approved,
}
args.out.parent.mkdir(parents=True, exist_ok=True)
args.out.write_text(json.dumps(anchor, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"trust_anchor": str(args.out), "sha256": sha256_file(args.out), "warning": "Store sha256 outside the evaluated repository"}))
