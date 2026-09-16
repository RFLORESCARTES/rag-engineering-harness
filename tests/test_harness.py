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

    def test_config_validates(self):
        self.assertEqual(load_config(self.work / "rag_harness.yaml")["version"], "0.3.0")

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
        config = ROOT / "profiles" / "r2-confidential.json"
        metrics = evaluate(self.work / "fixtures/enterprise_gold.jsonl", self.work / "fixtures/enterprise_run_pass.jsonl", config, self.work / "enterprise-pass")
        result = gate(metrics, config)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["dimensions"]["authorization"], "PASS")
        self.assertEqual(result["dimensions"]["privacy_security"], "PASS")

    def test_enterprise_profile_fails_cross_tenant_leak(self):
        config = ROOT / "profiles" / "r2-confidential.json"
        metrics = evaluate(self.work / "fixtures/enterprise_gold.jsonl", self.work / "fixtures/enterprise_run_leak.jsonl", config, self.work / "enterprise-leak")
        result = gate(metrics, config)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(result["dimensions"]["privacy_security"], "FAIL")
        self.assertGreater(metrics["metrics"]["critical_security_failures"], 0)


if __name__ == "__main__":
    unittest.main()
