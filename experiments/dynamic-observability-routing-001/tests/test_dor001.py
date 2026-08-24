import json
import unittest
from dataclasses import asdict

from dor001.core import EvidenceReceipt, EvidenceState, Observation, Router
from dor001.evaluator import ExternalOracle, replay_policy, run_all
from dor001.fixture import Scenario, frozen_manifest, frozen_scenarios


class DOR001Tests(unittest.TestCase):
    def test_manifest_has_required_sentinel_and_budget(self):
        manifest = frozen_manifest()
        manifest.validate()
        self.assertEqual(manifest.budget_per_tick, 2)
        sentinels = [c for c in manifest.channels if c.mandatory_sentinel]
        self.assertEqual([c.channel_id for c in sentinels], ["sentinel"])
        self.assertTrue(all(c.provenance and c.resolution for c in manifest.channels))

    def test_receipt_conditioning_changes_route(self):
        router = Router(frozen_manifest())
        alpha = EvidenceState(0, (EvidenceReceipt("a", 0, ("alpha",)),), ())
        beta = EvidenceState(0, (EvidenceReceipt("b", 0, ("beta",)),), ())
        self.assertIn("diag_alpha", router.select("x", alpha).selected_channels)
        self.assertIn("diag_beta", router.select("x", beta).selected_channels)

    def test_future_receipt_is_rejected(self):
        state = EvidenceState(0, (EvidenceReceipt("future", 1, ("alpha",)),), ())
        with self.assertRaises(ValueError):
            _ = state.routing_tags

    def test_router_explores_after_clean_measurement(self):
        router = Router(frozen_manifest())
        receipt = EvidenceReceipt("a", 0, ("alpha",))
        first = router.select("x", EvidenceState(0, (receipt,), ()))
        self.assertIn("diag_alpha", first.selected_channels)
        second_state = EvidenceState(
            3,
            (receipt,),
            (
                Observation(0, "diag_alpha", 0.0),
                Observation(0, "sentinel", 0.0),
                Observation(1, "diag_alpha", 0.0),
                Observation(1, "sentinel", 0.0),
                Observation(2, "diag_alpha", 0.0),
                Observation(2, "sentinel", 0.0),
            ),
        )
        second = router.select("x", second_state)
        self.assertNotEqual(first.selected_channels, second.selected_channels)

    def test_measurement_receipt_has_no_runtime_authority(self):
        router = Router(frozen_manifest())
        state = EvidenceState(0, (EvidenceReceipt("a", 0, ("alpha",)),), ())
        receipt = router.select("x", state)
        self.assertEqual(receipt.runtime_permission, "NONE")
        self.assertEqual(receipt.expires_at, 1)
        self.assertEqual(receipt.budget_limit, 2)
        self.assertEqual(receipt.budget_spent, 2)
        self.assertTrue(receipt.receipt_hash)
        self.assertIn("diag_alpha", receipt.reason)

    def test_external_oracle_blocks_nuisance_positive(self):
        scenario = next(s for s in frozen_scenarios() if s.scenario_id == "ho-nuisance-alpha")
        oracle = ExternalOracle()
        observations = (Observation(1, "diag_alpha", 1.0),)
        self.assertFalse(oracle.resolved(scenario, observations, 1))

    def test_all_policies_use_equal_budget_and_sentinel(self):
        for scenario in frozen_scenarios():
            for policy in ("dor", "fixed_headline", "equal_budget_wide"):
                row = replay_policy(scenario, policy)
                for receipt in row["measurement_receipts"]:
                    self.assertEqual(receipt["budget_limit"], 2)
                    self.assertEqual(receipt["budget_spent"], 2)
                    self.assertIn("sentinel", receipt["selected_channels"])
                    self.assertEqual(receipt["runtime_permission"], "NONE")

    def test_fixture_contains_win_tie_and_loss_shapes(self):
        result = run_all()
        deltas = [d["delta_tau_vs_equal_budget_wide"] for d in result["heldout_deltas"]]
        self.assertTrue(any(d > 0 for d in deltas))
        self.assertTrue(any(d == 0 for d in deltas))
        self.assertTrue(any(d < 0 for d in deltas))

    def test_router_cannot_see_oracle_fields(self):
        router = Router(frozen_manifest())
        state = EvidenceState(0, (EvidenceReceipt("a", 0, ("alpha",)),), ())
        receipt = router.select("opaque", state)
        serialized = json.dumps(asdict(receipt), sort_keys=True)
        self.assertNotIn("reveal_times", serialized)
        self.assertNotIn("oracle_diagnostic_channels", serialized)
        self.assertNotIn("mechanism_id", serialized)

    def test_frozen_result_is_no_routing_advantage(self):
        result = run_all()
        self.assertEqual(result["verdict"], "NO_ROUTING_ADVANTAGE")
        self.assertEqual(result["primary_metrics"]["median_delta_tau_vs_fixed_headline"], 1.5)
        self.assertEqual(result["primary_metrics"]["median_delta_tau_vs_equal_budget_wide"], 0.0)
        self.assertEqual(result["primary_metrics"]["false_resolution_events"]["dor"], 0)


if __name__ == "__main__":
    unittest.main()
