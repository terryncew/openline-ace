from __future__ import annotations

import json
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from far006.controls import run_controls
from far006.experiment import adjudicate
from far006.external_task import load_task, verify_local_artifacts


class FAR006Tests(unittest.TestCase):
    def test_external_task_is_independent_and_pinned(self):
        task = load_task(ROOT)
        self.assertEqual(task["source_tier"], "INDEPENDENT_SWE_BENCH_VERIFIED_TASK")
        self.assertEqual(task["instance_id"], "pallets__flask-5014")
        self.assertEqual(task["base_commit"], "7ee9ceb71e868944a46e1ff00b506772a53a4f1d")
        self.assertTrue(verify_local_artifacts(ROOT, task)["passed"])

    def test_candidate_scope_is_source_only(self):
        task = load_task(ROOT)
        self.assertEqual(task["historical_fix"]["changed_paths"], ["src/flask/blueprints.py"])
        self.assertEqual(task["oracle"]["fail_to_pass"], ["tests/test_blueprints.py::test_empty_name_not_allowed"])
        self.assertNotEqual(
            task["historical_fix"]["patch_sha256"],
            task["oracle"]["test_patch_sha256"],
        )

    def test_power_controls(self):
        self.assertTrue(run_controls(ROOT)["passed"])

    def test_adjudication_is_boundary_exact(self):
        preregistration = json.loads((ROOT / "PREREGISTRATION.json").read_text())
        metrics = {
            key.removeprefix("required_"): value
            for key, value in preregistration["thresholds"].items()
        }
        integrity = {
            "external_source_hashes_match": True,
            "external_task_manifest_hashes_match": True,
            "historical_patch_bytes_match_swe_bench": True,
            "oracle_patch_bytes_match_swe_bench": True,
            "primary_python_matches": True,
            "upstream_assurance_pins_match": True,
        }
        self.assertEqual(adjudicate(preregistration, metrics, integrity), preregistration["success_verdict"])
        metrics["historical_fix_promotion_rate"] = 0.0
        self.assertEqual(adjudicate(preregistration, metrics, integrity), preregistration["failure_verdict"])
        integrity["external_source_hashes_match"] = False
        self.assertEqual(adjudicate(preregistration, metrics, integrity), preregistration["invalid_verdict"])


if __name__ == "__main__":
    unittest.main()
