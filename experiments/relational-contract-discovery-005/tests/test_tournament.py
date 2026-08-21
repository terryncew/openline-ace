from __future__ import annotations

import unittest

from rcdl005.tournament import run_tournament, verify_exhaustive_oracle


class TournamentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result, cls.rows = run_tournament()

    def test_exhaustive_oracle(self) -> None:
        self.assertEqual(verify_exhaustive_oracle()["oracle_comparisons"], 144)

    def test_tournament_is_valid(self) -> None:
        self.assertEqual(self.result["protocol_status"], "VALID_RESULT")

    def test_scientific_verdict_is_parity(self) -> None:
        self.assertEqual(self.result["scientific_verdict"], "CAUSAL_UTILITY_PARITY")

    def test_record_count(self) -> None:
        self.assertEqual(len(self.rows), 1024)

    def test_every_contract_is_correct(self) -> None:
        self.assertTrue(all(row["correct_contract"] for row in self.rows))

    def test_non_identifiability_is_reported(self) -> None:
        ambiguous = [row for row in self.rows if row["observable_class"] == "class-03"]
        self.assertTrue(ambiguous)
        self.assertTrue(all(row["structural_status"] == "NON_IDENTIFIABLE" for row in ambiguous))

    def test_transport_and_nuisance_checks_pass(self) -> None:
        self.assertTrue(self.result["checks"]["transport_across_implementations"])
        self.assertTrue(self.result["checks"]["nuisance_stability"])

    def test_no_sham_failed(self) -> None:
        self.assertTrue(all(row["sham_failures"] == 0 for row in self.rows))


if __name__ == "__main__":
    unittest.main()

