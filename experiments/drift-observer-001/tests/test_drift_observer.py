from __future__ import annotations

from dataclasses import replace
import unittest

from drift_observer.baseline import mint_successor_baseline
from drift_observer.fixture import CLAIMS, DOMAIN_SPECS, baseline, current, run_fixture
from drift_observer.model import DimensionSpec, StateSnapshot
from drift_observer.observer import DriftObserver


def impact_map(observation):
    return {
        impact.claim_id: impact.disposition
        for impact in observation.claim_impacts
    }


class DriftObserverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = baseline()
        self.seed = current(self.base)
        self.observer = DriftObserver(DOMAIN_SPECS)

    def test_unchanged_state_retains_all_claims(self) -> None:
        obs = self.observer.observe(
            baseline=self.base,
            current=self.seed,
            claims=CLAIMS,
        )
        self.assertEqual(obs.status, "WITHIN_DECLARED_ENVELOPE")
        self.assertFalse(obs.crossed_dimensions)
        self.assertEqual(set(impact_map(obs).values()), {"RETAIN"})

    def test_readme_change_reopens_only_docs(self) -> None:
        state = replace(
            self.seed,
            domain={**self.seed.domain, "readme_hash": "docs-B"},
        )
        obs = self.observer.observe(
            baseline=self.base,
            current=state,
            claims=CLAIMS,
        )
        impacts = impact_map(obs)
        self.assertEqual(obs.crossed_dimensions, ("readme_hash",))
        self.assertEqual(impacts["docs-reviewed"], "REOPEN")
        self.assertEqual(impacts["merge-current-patch"], "RETAIN")
        self.assertEqual(impacts["control-stable"], "RETAIN")

    def test_patch_rebind_reopens_merge_not_docs(self) -> None:
        state = replace(
            self.seed,
            control_plane={
                **self.seed.control_plane,
                "action_binding": "commit-B",
                "evidence_bundle_hash": "evidence-B",
                "evidence_epoch": 8,
            },
            domain={**self.seed.domain, "code_hash": "code-B"},
        )
        obs = self.observer.observe(
            baseline=self.base,
            current=state,
            claims=CLAIMS,
        )
        impacts = impact_map(obs)
        self.assertEqual(impacts["merge-current-patch"], "REOPEN")
        self.assertEqual(impacts["docs-reviewed"], "RETAIN")
        self.assertEqual(impacts["control-stable"], "RETAIN")

    def test_small_numeric_displacement_stays_inside_envelope(self) -> None:
        state = replace(
            self.seed,
            domain={**self.seed.domain, "sensor_bias_micros": 15_000},
        )
        obs = self.observer.observe(
            baseline=self.base,
            current=state,
            claims=CLAIMS,
        )
        self.assertNotIn("sensor_bias_micros", obs.crossed_dimensions)
        self.assertEqual(obs.status, "WITHIN_DECLARED_ENVELOPE")

    def test_large_numeric_displacement_saturates_and_reopens(self) -> None:
        state = replace(
            self.seed,
            domain={**self.seed.domain, "sensor_bias_micros": 250_000},
        )
        obs = self.observer.observe(
            baseline=self.base,
            current=state,
            claims=CLAIMS,
        )
        impacts = impact_map(obs)
        self.assertIn("sensor_bias_micros", obs.crossed_dimensions)
        self.assertIn("sensor_bias_micros", obs.saturated_dimensions)
        self.assertEqual(impacts["control-stable"], "REOPEN")
        self.assertEqual(impacts["telemetry-safe"], "ACE_RECOMMENDED")

    def test_witness_version_is_non_optional_control_dimension(self) -> None:
        state = replace(
            self.seed,
            control_plane={**self.seed.control_plane, "witness_version": 4},
        )
        obs = self.observer.observe(
            baseline=self.base,
            current=state,
            claims=CLAIMS,
        )
        self.assertIn("witness_version", obs.crossed_dimensions)
        self.assertEqual(impact_map(obs)["merge-current-patch"], "REOPEN")

    def test_missing_policy_hash_is_detected(self) -> None:
        control = dict(self.seed.control_plane)
        control.pop("policy_hash")
        state = StateSnapshot(
            reference_receipt_id=self.seed.reference_receipt_id,
            observed_at=self.seed.observed_at,
            control_plane=control,
            domain=self.seed.domain,
        )
        obs = self.observer.observe(
            baseline=self.base,
            current=state,
            claims=CLAIMS,
        )
        component = next(item for item in obs.delta_hol if item.name == "policy_hash")
        self.assertTrue(component.missing)
        self.assertTrue(component.crossed)

    def test_receiver_cannot_override_mandatory_control_spec(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "mandatory_control_dimension_override",
        ):
            DriftObserver(
                (
                    DimensionSpec(
                        "policy_hash",
                        "numeric",
                        epsilon_micros=999_999,
                        scale=1,
                    ),
                )
            )

    def test_expired_baseline_reopens_all_without_calling_it_drift(self) -> None:
        obs = self.observer.observe(
            baseline=self.base,
            current=self.seed,
            claims=CLAIMS,
            now="2026-08-21T20:00:01Z",
        )
        self.assertEqual(obs.status, "BASELINE_REVERIFY_REQUIRED")
        self.assertFalse(obs.delta_hol)
        self.assertEqual(set(impact_map(obs).values()), {"REOPEN"})

    def test_revoked_support_reopens_all(self) -> None:
        revoked = replace(self.base, support_standing="REVOKED")
        obs = self.observer.observe(
            baseline=revoked,
            current=self.seed,
            claims=CLAIMS,
        )
        self.assertEqual(obs.status, "BASELINE_REVERIFY_REQUIRED")
        self.assertEqual(set(impact_map(obs).values()), {"REOPEN"})

    def test_successful_reverification_mints_successor_not_mutation(self) -> None:
        prior_id = self.base.receipt_id
        successor = mint_successor_baseline(
            previous=self.base,
            verified_state=self.seed,
            verified_at="2026-08-21T18:15:00Z",
        )
        self.assertEqual(self.base.receipt_id, prior_id)
        self.assertNotEqual(successor.receipt_id, prior_id)
        self.assertEqual(successor.parent_receipt_id, prior_id)

    def test_display_scalar_is_never_authority(self) -> None:
        obs = self.observer.observe(
            baseline=self.base,
            current=self.seed,
            claims=CLAIMS,
        )
        self.assertFalse(obs.display_scalar_authoritative)
        self.assertEqual(obs.policy_authority, "NONE")
        self.assertEqual(obs.runtime_permission, "NONE")

    def test_wrong_reference_receipt_reopens_dependent_claim(self) -> None:
        state = replace(
            self.seed,
            reference_receipt_id="sv-wrong-reference",
        )
        obs = self.observer.observe(
            baseline=self.base,
            current=state,
            claims=CLAIMS,
        )
        self.assertIn("reference_receipt", obs.crossed_dimensions)
        self.assertEqual(impact_map(obs)["merge-current-patch"], "REOPEN")

    def test_fixture_closes_expected_claim_boundary(self) -> None:
        result = run_fixture()
        self.assertEqual(
            result["status"],
            "VERIFIED_CONTINUITY_CONFORMANCE_PASS",
        )
        self.assertFalse(result["display_scalar_authoritative"])
        self.assertEqual(result["policy_authority"], "NONE")
        self.assertEqual(result["runtime_permission"], "NONE")


if __name__ == "__main__":
    unittest.main()
