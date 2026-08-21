from __future__ import annotations

import unittest

from rcdl007.tournament import run_tournament


class TournamentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_tournament()

    def test_frozen_row_count(self) -> None:
        self.assertEqual(len(self.result["rows"]), 640)

    def test_exact_parity(self) -> None:
        symbolic = self.result["metrics"]["symbolic"]
        learned = self.result["metrics"]["learned"]
        self.assertEqual(symbolic["correct"], 320)
        self.assertEqual(learned["correct"], 320)
        self.assertEqual(symbolic["accuracy_ppm"], 1_000_000)
        self.assertEqual(learned["accuracy_ppm"], 1_000_000)
        self.assertEqual(symbolic["query_total"], 544)
        self.assertEqual(learned["query_total"], 544)
        self.assertEqual(symbolic["mean_queries"], 1.7)
        self.assertEqual(learned["mean_queries"], 1.7)
        self.assertEqual(symbolic["max_queries"], 2)
        self.assertEqual(learned["max_queries"], 2)

    def test_transport_and_verdict(self) -> None:
        self.assertEqual(self.result["transport_failures"], 0)
        self.assertEqual(self.result["verdict"], "PRE_ADJUDICATION_CAUSAL_PARITY")
        self.assertEqual(self.result["claim_effect"], "UNIQUE_PRE_ADJUDICATION_UTILITY_NOT_FOUND")
        self.assertEqual(self.result["authority"], "NONE")


if __name__ == "__main__":
    unittest.main()
