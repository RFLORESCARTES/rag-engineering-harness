from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from rag_harness.errors import BlockedError
from rag_harness.evaluator import evaluate
from rag_harness.gate import gate
from rag_harness.io import load_config
from rag_harness.integrity import evaluator_hash, sha256_file


ROOT = Path(__file__).resolve().parents[1]


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)
        for name in ("rag_harness.yaml",):
            shutil.copy2(ROOT / name, self.work / name)
        shutil.copytree(ROOT / "tests" / "fixtures", self.work / "fixtures")

    def tearDown(self):
        self.temp.cleanup()

    def enterprise_contract(self, audit_name="enterprise_audit_pass.jsonl"):
        config = ROOT / "profiles" / "r2-confidential.json"
        gold = self.work / "fixtures/enterprise_gold.jsonl"
        manifest = self.work / "fixtures/enterprise_corpus.jsonl"
        audit_log = self.work / f"fixtures/{audit_name}"
        anchor = self.work / "external-trust-anchor.json"
        anchor.write_text(json.dumps({
            "schema_version": "1.0",
            "minimum_risk_profile": "R2",
            "approved": {
                "evaluator_sha256": evaluator_hash(),
                "gold_sha256": sha256_file(gold),
                "config_sha256": sha256_file(config),
                "corpus_manifest_sha256": sha256_file(manifest),
                "audit_log_sha256": sha256_file(audit_log),
            },
        }, sort_keys=True))
        return config, gold, manifest, audit_log, anchor, sha256_file(anchor)

    def test_config_validates(self):
        self.assertEqual(load_config(self.work / "rag_harness.yaml")["version"], "0.4.0")

    def test_smoke_fixture_passes(self):
        metrics = evaluate(self.work / "fixtures/gold.jsonl", self.work / "fixtures/run.jsonl", self.work / "rag_harness.yaml", self.work / "report")
        result = gate(metrics, self.work / "rag_harness.yaml")
        self.assertEqual(result["verdict"], "PASS")

    def test_bad_run_fails_without_becoming_blocked(self):
        metrics = evaluate(self.work / "fixtures/gold.jsonl", self.work / "fixtures/run_fail.jsonl", self.work / "rag_harness.yaml", self.work / "report")
        result = gate(metrics, self.work / "rag_harness.yaml")
        self.assertEqual(result["verdict"], "FAIL")

    def test_config_mutation_blocks_gate(self):
        config = self.work / "rag_harness.yaml"
        metrics = evaluate(self.work / "fixtures/gold.jsonl", self.work / "fixtures/run.jsonl", config, self.work / "report")
        data = json.loads(config.read_text())
        data["thresholds"]["recall_at_k"] = 0.0
        config.write_text(json.dumps(data))
        with self.assertRaisesRegex(BlockedError, "config changed"):
            gate(metrics, config)

    def test_query_set_mismatch_blocks(self):
        run = self.work / "fixtures/run.jsonl"
        run.write_text(run.read_text().splitlines()[0] + "\n")
        with self.assertRaisesRegex(BlockedError, "missing="):
            evaluate(self.work / "fixtures/gold.jsonl", run, self.work / "rag_harness.yaml", self.work / "report")

    def test_metrics_tampering_blocks_gate(self):
        metrics = evaluate(self.work / "fixtures/gold.jsonl", self.work / "fixtures/run.jsonl", self.work / "rag_harness.yaml", self.work / "report")
        metrics["metrics"]["citation_precision"] = 0.123456
        with self.assertRaisesRegex(BlockedError, "differs from recomputation"):
            gate(metrics, self.work / "rag_harness.yaml")

    def test_required_manifest_blocks_when_absent(self):
        config = self.work / "rag_harness.yaml"
        data = json.loads(config.read_text())
        data["evaluation"]["require_corpus_manifest"] = True
        config.write_text(json.dumps(data))
        with self.assertRaisesRegex(BlockedError, "manifest"):
            evaluate(self.work / "fixtures/gold.jsonl", self.work / "fixtures/run.jsonl", config, self.work / "report")

    def test_manifest_mutation_blocks_gate(self):
        manifest = self.work / "corpus_manifest.jsonl"
        manifest.write_text("".join(json.dumps({"doc_id": doc}) + "\n" for doc in ("geo-fr-1", "spec-status", "readme-status", "ir-mrr")))
        metrics = evaluate(self.work / "fixtures/gold.jsonl", self.work / "fixtures/run.jsonl", self.work / "rag_harness.yaml", self.work / "report", manifest)
        manifest.write_text(manifest.read_text() + '{"doc_id":"changed"}\n')
        with self.assertRaisesRegex(BlockedError, "corpus_manifest changed"):
            gate(metrics, self.work / "rag_harness.yaml")

    def test_enterprise_profile_passes_authorized_run(self):
        config, gold, manifest, audit_log, anchor, digest = self.enterprise_contract()
        metrics = evaluate(gold, self.work / "fixtures/enterprise_run_pass.jsonl", config, self.work / "enterprise-pass", manifest, anchor, digest, audit_log)
        result = gate(metrics, config, trust_anchor=anchor, trust_anchor_sha256=digest, audit_log=audit_log)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["dimensions"]["authorization"], "PASS")
        self.assertEqual(result["dimensions"]["privacy_security"], "PASS")

    def test_enterprise_profile_fails_cross_tenant_leak(self):
        config, gold, manifest, audit_log, anchor, digest = self.enterprise_contract("enterprise_audit_leak.jsonl")
        metrics = evaluate(gold, self.work / "fixtures/enterprise_run_leak.jsonl", config, self.work / "enterprise-leak", manifest, anchor, digest, audit_log)
        result = gate(metrics, config, trust_anchor=anchor, trust_anchor_sha256=digest, audit_log=audit_log)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(result["dimensions"]["privacy_security"], "FAIL")
        self.assertGreater(metrics["metrics"]["critical_security_failures"], 0)

    def test_enterprise_requires_external_trust_root(self):
        config, gold, manifest, audit_log, anchor, _ = self.enterprise_contract()
        with self.assertRaisesRegex(BlockedError, "outside the evaluated repository"):
            evaluate(gold, self.work / "fixtures/enterprise_run_pass.jsonl", config, self.work / "no-root", manifest, anchor, audit_log=audit_log)

    def test_trust_anchor_prevents_profile_or_gold_substitution(self):
        config, gold, manifest, audit_log, anchor, digest = self.enterprise_contract()
        replacement = self.work / "replacement-gold.jsonl"
        replacement.write_text(gold.read_text().replace("tenant-a-contract", "tenant-b-contract"))
        with self.assertRaisesRegex(BlockedError, "gold_sha256"):
            evaluate(replacement, self.work / "fixtures/enterprise_run_pass.jsonl", config, self.work / "substitution", manifest, anchor, digest, audit_log)

    def test_fabricated_audit_is_not_self_attesting(self):
        config, gold, manifest, audit_log, anchor, digest = self.enterprise_contract()
        run = self.work / "fixtures/enterprise_run_pass.jsonl"
        forged = self.work / "forged-run.jsonl"
        forged.write_text(run.read_text().replace('"decision":"DENY_CROSS_TENANT"', '"decision":"ANSWER"'))
        with self.assertRaisesRegex(BlockedError, "not corroborated"):
            evaluate(gold, forged, config, self.work / "forged", manifest, anchor, digest, audit_log)

    def test_partial_query_set_does_not_crash_when_allowed(self):
        config = self.work / "rag_harness.yaml"
        data = json.loads(config.read_text())
        data["evaluation"]["require_complete_query_set"] = False
        config.write_text(json.dumps(data))
        run = self.work / "fixtures/run.jsonl"
        run.write_text(run.read_text().splitlines()[0] + "\n")
        metrics = evaluate(self.work / "fixtures/gold.jsonl", run, config, self.work / "partial")
        self.assertEqual(metrics["evaluated_query_count"], 1)
        self.assertEqual(metrics["query_coverage"], 0.25)

    def test_zero_grade_for_relevant_document_blocks(self):
        gold = self.work / "fixtures/gold.jsonl"
        gold.write_text(gold.read_text().replace('"geo-fr-1":2', '"geo-fr-1":0'))
        with self.assertRaisesRegex(BlockedError, "positive graded_relevance"):
            evaluate(gold, self.work / "fixtures/run.jsonl", self.work / "rag_harness.yaml", self.work / "zero-grade")


if __name__ == "__main__":
    unittest.main()
