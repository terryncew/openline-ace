from __future__ import annotations

import csv
import hashlib
import json
import random
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from is002.core import audit_rows, load_policy
from is002.external import build_unitree_rows, sha256_file, unitree_risk_bucket
from is002.fixtures import (
    deterministic_global_control,
    deterministic_state_specific_control,
    stochastic_state_specific_control,
    validated_model_state_specific_control,
)


class InterventionSufficiency002Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_policy()

    def test_global_action_delay_shortcut_is_rejected(self) -> None:
        report = audit_rows(deterministic_global_control(), self.policy)
        self.assertEqual(
            report["verdict"],
            "INSUFFICIENT_STATE_SPECIFIC_INTERVENTION_CONTRAST",
        )
        self.assertFalse(
            report["gates"]["state_dependent_action_lag_strata"]["passed"]
        )
        self.assertFalse(
            report["gates"]["bidirectional_remedy_divergent_risk_pairs"][
                "passed"
            ]
        )
        self.assertFalse(
            report["gates"]["global_action_delay_cell_accuracy"]["passed"]
        )

    def test_deterministic_single_trial_cells_clear(self) -> None:
        report = audit_rows(deterministic_state_specific_control(), self.policy)
        self.assertEqual(
            report["verdict"], "SUFFICIENT_FOR_FRESH_TRANSITION_CONFIRMATION"
        )
        self.assertEqual(report["evidence_mode"], "deterministic_rollout")
        self.assertTrue(all(gate["passed"] for gate in report["gates"].values()))
        self.assertTrue(report["transition_confirmation_authorized"])
        self.assertFalse(report["capacity_selector_training_authorized"])

    def test_stochastic_cells_require_and_accept_four_trials(self) -> None:
        rows = stochastic_state_specific_control()
        report = audit_rows(rows, self.policy)
        self.assertEqual(
            report["verdict"], "SUFFICIENT_FOR_FRESH_TRANSITION_CONFIRMATION"
        )
        short = [row for row in rows if row["replicate"] != 3]
        short_report = audit_rows(short, self.policy)
        self.assertEqual(
            short_report["verdict"],
            "INSUFFICIENT_STATE_SPECIFIC_INTERVENTION_CONTRAST",
        )
        self.assertFalse(
            short_report["gates"]["complete_context_rate"]["passed"]
        )

    def test_validated_model_requires_receipt(self) -> None:
        rows = validated_model_state_specific_control()
        report = audit_rows(rows, self.policy)
        self.assertEqual(
            report["verdict"], "SUFFICIENT_FOR_FRESH_TRANSITION_CONFIRMATION"
        )
        rows[0] = deepcopy(rows[0])
        rows[0].pop("model_validation_receipt_sha256")
        invalid = audit_rows(rows, self.policy)
        self.assertEqual(invalid["verdict"], "INVALID_EXTERNAL_INTERVENTION_CORPUS")

    def test_deterministic_pseudoreplication_is_invalid(self) -> None:
        rows = deterministic_state_specific_control()
        duplicate = deepcopy(rows[0])
        duplicate["trial_id"] = "unique-but-duplicated-deterministic-cell"
        rows.append(duplicate)
        report = audit_rows(rows, self.policy)
        self.assertEqual(report["verdict"], "INVALID_EXTERNAL_INTERVENTION_CORPUS")

    def test_order_does_not_change_receipt(self) -> None:
        rows = deterministic_state_specific_control()
        original = audit_rows(rows, self.policy)
        random.Random(20260830).shuffle(rows)
        shuffled = audit_rows(rows, self.policy)
        self.assertEqual(original, shuffled)

    def test_context_snapshot_mutation_is_invalid(self) -> None:
        rows = deterministic_state_specific_control()
        rows[1] = deepcopy(rows[1])
        rows[1]["snapshot_sha256"] = "0" * 64
        report = audit_rows(rows, self.policy)
        self.assertEqual(report["verdict"], "INVALID_EXTERNAL_INTERVENTION_CORPUS")
        self.assertIn("snapshot changed", report["errors"][0])

    def test_context_risk_projection_mutation_is_invalid(self) -> None:
        rows = deterministic_state_specific_control()
        rows[1] = deepcopy(rows[1])
        rows[1]["apparent_risk_bucket"] = "changed-after-outcome"
        report = audit_rows(rows, self.policy)
        self.assertEqual(report["verdict"], "INVALID_EXTERNAL_INTERVENTION_CORPUS")

    def test_authority_claim_is_invalid(self) -> None:
        rows = deterministic_state_specific_control()
        rows[0] = deepcopy(rows[0])
        rows[0]["policy_authority"] = "EXECUTE"
        report = audit_rows(rows, self.policy)
        self.assertEqual(report["verdict"], "INVALID_EXTERNAL_INTERVENTION_CORPUS")

    def test_missing_required_action_fails_closed(self) -> None:
        rows = [
            row
            for row in deterministic_state_specific_control()
            if row["action_id"] != "CONTINUE"
        ]
        report = audit_rows(rows, self.policy)
        self.assertEqual(
            report["verdict"],
            "INSUFFICIENT_STATE_SPECIFIC_INTERVENTION_CONTRAST",
        )
        self.assertFalse(report["gates"]["actions"]["passed"])

    def test_unitree_risk_bucket_excludes_direction_and_phase(self) -> None:
        left = {
            "push_force_newtons": 240.0,
            "push_pitch_torque_nm": -30.0,
            "push_direction_x": -1.0,
            "phase_offset_seconds": 0.0,
        }
        right = {
            "push_force_newtons": 240.0,
            "push_pitch_torque_nm": 30.0,
            "push_direction_x": 1.0,
            "phase_offset_seconds": 0.16,
        }
        self.assertEqual(unitree_risk_bucket(left), unitree_risk_bucket(right))

    def test_unitree_adapter_preserves_exact_deterministic_cells(self) -> None:
        fixture = deterministic_state_specific_control()
        with tempfile.TemporaryDirectory() as temporary:
            stage_a = Path(temporary)
            context_ids = sorted({row["context_id"] for row in fixture})
            context_receipts = []
            for context_id in context_ids:
                pair = int(context_id.split(":")[0].split("-")[1])
                side = context_id.rsplit(":", 1)[1]
                context_receipts.append(
                    {
                        "context_id": context_id,
                        "integration_state_sha256": hashlib.sha256(
                            f"integration:{context_id}".encode()
                        ).hexdigest(),
                        "wrapper_state_sha256": hashlib.sha256(
                            f"wrapper:{context_id}".encode()
                        ).hexdigest(),
                        "push_force_newtons": float(120 + pair),
                        "push_pitch_torque_nm": -30.0 if side == "a" else 30.0,
                        "push_direction_x": -1.0 if side == "a" else 1.0,
                        "phase_offset_seconds": 0.0 if side == "a" else 0.16,
                    }
                )
            (stage_a / "context_receipts.json").write_text(
                json.dumps(context_receipts, sort_keys=True) + "\n"
            )

            dataset = stage_a / "intervention_sufficiency_input.csv"
            fields = [
                "context_id",
                "action_id",
                "lag",
                "target_id",
                "constraint_set_id",
                "trial_id",
                "outcome_success",
            ]
            with dataset.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for row in fixture:
                    writer.writerow(
                        {
                            "context_id": row["context_id"],
                            "action_id": row["action_id"],
                            "lag": row["lag_ms"],
                            "target_id": "upright_stable_1p2s",
                            "constraint_set_id": "released_g1_model_and_pd_limits",
                            "trial_id": row["trial_id"],
                            "outcome_success": int(row["outcome_success"]),
                        }
                    )
            upstream = {
                "evidence_mode": "deterministic_rollout",
                "matching_frozen_before_outcome_analysis": True,
                "dataset_receipt_sha256": sha256_file(dataset),
            }
            upstream_path = stage_a / "intervention_sufficiency_manifest.json"
            upstream_path.write_text(json.dumps(upstream, sort_keys=True) + "\n")
            source_manifest = {
                "dataset_sha256": sha256_file(dataset),
                "context_receipts_sha256": sha256_file(
                    stage_a / "context_receipts.json"
                ),
                "stage_a_manifest_sha256": sha256_file(upstream_path),
                "expected_contexts": 50,
                "expected_cells": 1500,
                "stage_a_run_id": 1,
            }
            converted = build_unitree_rows(stage_a, source_manifest)
            self.assertEqual(len(converted), 1500)
            self.assertEqual(
                len(
                    {
                        (
                            row["context_id"],
                            row["action_id"],
                            row["lag_ms"],
                        )
                        for row in converted
                    }
                ),
                1500,
            )
            report = audit_rows(converted, self.policy)
            self.assertEqual(
                report["verdict"],
                "SUFFICIENT_FOR_FRESH_TRANSITION_CONFIRMATION",
            )


if __name__ == "__main__":
    unittest.main()
