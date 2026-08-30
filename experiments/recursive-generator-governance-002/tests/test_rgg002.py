import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rgg002.progress import calibration, generator_progress, initial_state, point_state


class TestRGG002(unittest.TestCase):
    def test_progress_calibration_is_powered(self):
        c = calibration()
        self.assertTrue(c["passed"])
        self.assertLessEqual(c["initial_panel_sd"], 0.0012)
        self.assertGreaterEqual(0.005 / c["initial_panel_sd"], 4.0)

    def test_progress_rewards_safe_speed_not_wrong_speed(self):
        risky = point_state("int32", "none", "length", 64)
        slow = point_state("python", "full", "full", 1)
        fast = point_state("int64", "full", "full", 64)
        rq = generator_progress(risky, seed="TEST", direct_case_count=192, relation_checks=32)["quality"]
        sq = generator_progress(slow, seed="TEST", direct_case_count=192, relation_checks=32)["quality"]
        fq = generator_progress(fast, seed="TEST", direct_case_count=192, relation_checks=32)["quality"]
        self.assertGreater(sq, rq + 0.20)
        self.assertGreater(fq, sq + 0.01)

    def test_progress_is_exact_expectation(self):
        q1 = generator_progress(initial_state(), seed="PAIR", direct_case_count=64, relation_checks=8)
        q2 = generator_progress(initial_state(), seed="PAIR", direct_case_count=64, relation_checks=8)
        self.assertEqual(q1, q2)

    def test_search_seeds_are_disjoint(self):
        p = json.loads((ROOT / "PREREGISTRATION.json").read_text())
        self.assertFalse(set(p["search_seeds"]) & set(p["rgg001_search_seeds_for_disjointness_check"]))
        self.assertEqual(16, len(set(p["search_seeds"])))

    def test_no_rgg001_external_holdout_import(self):
        text = (ROOT / "rgg002/progress.py").read_text() + (ROOT / "rgg002/experiment.py").read_text()
        self.assertNotIn("external_direct_cases", text)
        self.assertNotIn("ExternalEvaluator", text)

    def test_no_quarantine_mechanism(self):
        text = (ROOT / "rgg002/experiment.py").read_text().lower()
        self.assertNotIn("quarantine", text)


if __name__ == "__main__":
    unittest.main()
