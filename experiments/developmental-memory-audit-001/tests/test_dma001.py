import unittest
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dma001.grader import grade_file, load_results

class DMA001Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = ROOT / "fixtures" / "conformance-results.jsonl"
        self.by_id = {r["candidate_id"]: r for r in grade_file(self.fixture)}

    def test_load_bearing_supported(self):
        self.assertEqual(self.by_id["planted.load_bearing"]["standing"], "SUPPORTED_LOAD_BEARING")

    def test_ritual_rejected(self):
        self.assertEqual(self.by_id["planted.ritual"]["standing"], "REJECTED_RITUAL")

    def test_sham_damage_abstains(self):
        self.assertEqual(self.by_id["planted.sham_sensitive"]["standing"], "ABSTAIN_SHAM_DAMAGE")

    def test_missing_restoration_incomplete(self):
        self.assertEqual(self.by_id["planted.no_restoration"]["standing"], "INCOMPLETE")

    def test_no_authority(self):
        for result in self.by_id.values():
            self.assertEqual(result["policy_authority"], "NONE")

    def test_specific_effect_metric(self):
        r = self.by_id["planted.load_bearing"]
        self.assertAlmostEqual(r["metrics"]["active_minus_sham_failure_delta"], 0.7)
        self.assertAlmostEqual(r["metrics"]["restoration_minus_active_success_delta"], 0.6)

    def test_duplicate_rejected(self):
        rows = load_results(self.fixture)
        rows.append(dict(rows[0]))
        from dma001.grader import grade_candidate
        with self.assertRaises(ValueError):
            grade_candidate(rows, rows[0]["candidate_id"])

if __name__ == "__main__":
    unittest.main()
