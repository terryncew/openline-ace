from __future__ import annotations

import random
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from is001.core import audit_rows, load_policy
from is001.fixtures import global_rule_control, state_specific_control


class InterventionSufficiencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_policy()

    def test_global_rule_is_rejected(self) -> None:
        report = audit_rows(global_rule_control(), self.policy)
        self.assertEqual(report["verdict"], "INSUFFICIENT_INTERVENTION_CONTRAST")
        self.assertFalse(report["gates"]["remedy_divergent_risk_pairs"]["passed"])
        self.assertFalse(report["gates"]["state_dependent_action_lag_strata"]["passed"])

    def test_state_specific_control_clears(self) -> None:
        report = audit_rows(state_specific_control(), self.policy)
        self.assertEqual(report["verdict"], "SUFFICIENT_FOR_STATE_CONDITIONED_TRANSITION_TEST")
        self.assertTrue(all(gate["passed"] for gate in report["gates"].values()))
        self.assertFalse(report["capacity_selector_training_authorized"])
        self.assertTrue(report["receipt_gate_required_for_execution"])

    def test_order_does_not_change_receipt(self) -> None:
        rows = state_specific_control()
        original = audit_rows(rows, self.policy)
        random.Random(19).shuffle(rows)
        shuffled = audit_rows(rows, self.policy)
        self.assertEqual(original, shuffled)

    def test_missing_cell_fails_closed(self) -> None:
        rows = [
            row
            for row in state_specific_control()
            if not (
                row["context_id"] == "severity-0:left"
                and row["action_id"] == "counter_right"
                and row["lag_ms"] == 0
            )
        ]
        report = audit_rows(rows, self.policy)
        self.assertEqual(report["verdict"], "INSUFFICIENT_INTERVENTION_CONTRAST")
        self.assertFalse(report["gates"]["complete_context_rate"]["passed"])

    def test_snapshot_mutation_is_invalid(self) -> None:
        rows = state_specific_control()
        rows[1] = deepcopy(rows[1])
        rows[1]["snapshot_sha256"] = "0" * 64
        report = audit_rows(rows, self.policy)
        self.assertEqual(report["verdict"], "INVALID_INTERVENTION_CORPUS")
        self.assertIn("snapshot changed", report["errors"][0])

    def test_authority_claim_is_invalid(self) -> None:
        rows = state_specific_control()
        rows[0] = deepcopy(rows[0])
        rows[0]["policy_authority"] = "EXECUTE"
        report = audit_rows(rows, self.policy)
        self.assertEqual(report["verdict"], "INVALID_INTERVENTION_CORPUS")

    def test_duplicate_trial_is_invalid(self) -> None:
        rows = state_specific_control()
        rows[1] = deepcopy(rows[1])
        rows[1]["trial_id"] = rows[0]["trial_id"]
        report = audit_rows(rows, self.policy)
        self.assertEqual(report["verdict"], "INVALID_INTERVENTION_CORPUS")

    def test_duplicate_replicate_index_is_invalid(self) -> None:
        rows = state_specific_control()
        rows[1] = deepcopy(rows[1])
        rows[1]["replicate"] = rows[0]["replicate"]
        rows[1]["trial_id"] = "otherwise-unique-trial"
        report = audit_rows(rows, self.policy)
        self.assertEqual(report["verdict"], "INVALID_INTERVENTION_CORPUS")


if __name__ == "__main__":
    unittest.main()
