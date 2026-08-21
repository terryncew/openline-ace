from __future__ import annotations

import unittest

from rcdl007.arena import (
    DEVELOPMENT_FAULTS,
    EVALUATION_FAULTS,
    PROBES,
    evaluation_scenarios,
    ledger_probe,
    passive_observation,
    queue_probe,
    standing_for_faults,
)
from rcdl007.model import Scenario, Standing


class ArenaTests(unittest.TestCase):
    def test_probe_menu_is_closed_and_opaque(self) -> None:
        self.assertEqual(len(PROBES), 10)
        self.assertEqual({probe.probe_id for probe in PROBES}, {f"probe-{i:02d}" for i in range(10)})

    def test_composition_holdout(self) -> None:
        overlap = set(DEVELOPMENT_FAULTS) & set(EVALUATION_FAULTS)
        self.assertEqual(overlap, {frozenset()})
        held_out = [faults for faults in EVALUATION_FAULTS if faults]
        self.assertTrue(all(faults not in DEVELOPMENT_FAULTS for faults in held_out))
        self.assertTrue(any(len(faults) == 4 for faults in held_out))

    def test_standing_partition(self) -> None:
        self.assertIs(standing_for_faults(frozenset()), Standing.NUISANCE)
        self.assertIs(standing_for_faults(frozenset({"freshness", "lineage"})), Standing.NATIVE)
        self.assertIs(standing_for_faults(frozenset({"submit_gate", "timeout_gate"})), Standing.IMPOSED)
        self.assertIs(standing_for_faults(frozenset({"freshness", "timeout_gate"})), Standing.MIXED)

    def test_independent_adapters_preserve_causal_bit(self) -> None:
        scenario = Scenario("adapter-check", frozenset({"freshness", "timeout_gate"}), 77)
        for probe in PROBES:
            ledger = ledger_probe(scenario, probe.probe_id)
            queue = queue_probe(scenario, probe.probe_id)
            self.assertEqual(ledger.external_success, queue.external_success)
            self.assertNotEqual(ledger.surface_tag, queue.surface_tag)

    def test_evaluation_identity_count(self) -> None:
        self.assertEqual(len(evaluation_scenarios(16)), 160)

    def test_passive_observation_contains_no_label(self) -> None:
        scenario = Scenario("raw-only", frozenset({"freshness"}), 12)
        observation = passive_observation(scenario, "ledger-v3")
        self.assertFalse(observation.external_success)
        self.assertFalse(hasattr(observation, "artifact_valid"))
        self.assertFalse(hasattr(observation, "standing"))


if __name__ == "__main__":
    unittest.main()
