from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sld001.core import evaluate, standing_loss_time


class SLD001Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads((ROOT / "frozen_cases.json").read_text())
        cls.prereg = json.loads((ROOT / "preregistration.json").read_text())

    def case(self, cid):
        return next(c for c in self.cases if c["case_id"] == cid)

    def test_standing_loss_uses_completed_reverification(self):
        self.assertEqual(standing_loss_time(self.case("C1")), 2)
        self.assertNotEqual(standing_loss_time(self.case("C1")), self.case("C1")["reopen"])

    def test_seamless_reverification_is_not_lost(self):
        self.assertIsNone(standing_loss_time(self.case("R1")))

    def test_benign_unbound_change_is_not_lost(self):
        self.assertIsNone(standing_loss_time(self.case("B1")))

    def test_hidden_dependency_is_missed(self):
        self.assertIsNone(standing_loss_time(self.case("H1")))

    def test_raw_failure_has_no_prior_signal(self):
        self.assertIsNone(standing_loss_time(self.case("F1")))

    def test_benign_revocation_loses_standing_even_if_output_passes(self):
        self.assertEqual(standing_loss_time(self.case("V1")), 3)
        self.assertEqual(self.case("V1")["headline_outcome"], "PASS")

    def test_result_counts_reopening_separately_from_lost(self):
        result = evaluate(self.cases, self.prereg)
        self.assertEqual(result["false_invalidation"]["olp"]["events"], 0)
        self.assertGreater(result["false_invalidation"]["naive_diff"]["events"], 0)

    def test_slow_reverification_can_lose_the_race(self):
        result = evaluate(self.cases, self.prereg)
        self.assertIn(-1, result["lead_time"]["olp"]["leads"])

    def test_hidden_dependency_misses_are_reported(self):
        result = evaluate(self.cases, self.prereg)
        self.assertEqual(result["coverage_limits"]["hidden_dependency_misses"], 2)

    def test_receipt_chain_is_deterministic(self):
        a = evaluate(self.cases, self.prereg)
        b = evaluate(self.cases, self.prereg)
        self.assertEqual(a["receipt_chain"]["head_sha256"], b["receipt_chain"]["head_sha256"])

    def test_insufficient_corpus_fails_closed(self):
        result = evaluate(self.cases[:3], self.prereg)
        self.assertEqual(result["verdict"], "DATA_INSUFFICIENT")

    def test_any_change_does_not_get_credit_for_precision(self):
        result = evaluate(self.cases, self.prereg)
        self.assertEqual(result["false_invalidation"]["naive_diff"]["rate"], 1.0)

    def test_falsifier_bites_if_reverification_is_too_slow(self):
        mutated = [dict(c) for c in self.cases]
        for c in mutated:
            if c["category"] == "consequential_invalidation":
                c["reverify_latency"] = 10
        result = evaluate(mutated, self.prereg)
        self.assertEqual(result["verdict"], "NO_STANDING_LOSS_ADVANTAGE")

    def test_falsifier_bites_if_olp_false_invalidates_controls(self):
        mutated = [dict(c) for c in self.cases]
        for c in mutated:
            if c["category"] == "mutation_with_seamless_reverification":
                c["reverify_outcome"] = "LOST"
        result = evaluate(mutated, self.prereg)
        self.assertEqual(result["verdict"], "NO_STANDING_LOSS_ADVANTAGE")

    def test_reopen_time_cannot_be_substituted_for_resolution_time(self):
        c = self.case("C4")
        reopen_lead = c["headline"] - c["reopen"]
        resolved_lead = c["headline"] - standing_loss_time(c)
        self.assertGreater(reopen_lead, 0)
        self.assertLess(resolved_lead, 0)


if __name__ == "__main__":
    unittest.main()
