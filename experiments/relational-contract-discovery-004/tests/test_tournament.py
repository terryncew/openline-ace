from __future__ import annotations

import unittest

from rcdl004.tournament import run_tournament


class TournamentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tournament, cls.predictions = run_tournament()

    def test_protocol_result_is_valid_even_when_rcdl_does_not_win(self) -> None:
        self.assertEqual(self.tournament["protocol_status"], "VALID_RESULT")
        self.assertEqual(self.tournament["scientific_verdict"], "LEARNED_PARITY")

    def test_frozen_audit_split_has_1024_rows(self) -> None:
        self.assertEqual(len(self.predictions), 1024)

    def test_learned_rule_set_matches_rcdl(self) -> None:
        self.assertEqual(self.tournament["best_learned_model"], "task_bag_relational_rule_set")
        self.assertEqual(self.tournament["best_learned_score"]["balanced_accuracy_ppm"], 1_000_000)
        self.assertEqual(
            self.tournament["best_learned_score"],
            self.tournament["rcdl_contract_predictor"]["test_score"],
        )

    def test_learned_models_never_receive_contracts_or_prediction_oracle(self) -> None:
        boundary = self.tournament["information_boundary"]
        self.assertFalse(boundary["clause_definitions_available_to_learned_models"])
        self.assertFalse(boundary["oracle_available_at_prediction"])
        self.assertFalse(boundary["intervention_or_hook_labels_available"])
        self.assertTrue(boundary["generic_cross_event_equality_available"])

    def test_neural_and_external_replication_gaps_remain_explicit(self) -> None:
        boundary = self.tournament["model_boundary"]
        self.assertFalse(boundary["neural_models_tested"])
        self.assertFalse(boundary["independent_developer_or_lab"])

    def test_prediction_rows_hide_model_inputs_beyond_opaque_ids(self) -> None:
        expected = {
            "schema", "example_id", "failed", "rcdl_prediction", "learned_predictions"
        }
        self.assertTrue(all(set(row) == expected for row in self.predictions))


if __name__ == "__main__":
    unittest.main()

