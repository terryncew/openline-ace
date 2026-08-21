from __future__ import annotations

import copy
import unittest

from rcdl005.domain import ACTION_BY_ID, ACTION_IDS, IMPLEMENTATIONS, final_scenarios
from rcdl005.execution import ProbeTrace, execute_pair, execute_probe, execute_recovery, parse_probe


class ExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenario = final_scenarios()[0]
        self.action = ACTION_IDS[0]

    def test_both_implementations_parse(self) -> None:
        for implementation in IMPLEMENTATIONS:
            pair = execute_pair(self.scenario, self.action, implementation)
            self.assertIsInstance(pair.active_outcome.failed, bool)

    def test_sham_never_breaks_behavior(self) -> None:
        for implementation in IMPLEMENTATIONS:
            for action in ACTION_IDS:
                self.assertFalse(execute_pair(self.scenario, action, implementation).sham_outcome.failed)

    def test_active_and_sham_energy_match(self) -> None:
        pair = execute_pair(self.scenario, ACTION_IDS[-1], "ledger")
        self.assertEqual(pair.active_outcome.energy_units, pair.sham_outcome.energy_units)

    def test_implementations_agree_on_outcome(self) -> None:
        for action in ACTION_IDS:
            ledger = execute_pair(self.scenario, action, "ledger")
            queue = execute_pair(self.scenario, action, "queue")
            self.assertEqual(ledger.active_outcome.failed, queue.active_outcome.failed)

    def test_unknown_action_rejected(self) -> None:
        with self.assertRaises(ValueError):
            execute_probe(self.scenario, "break:unknown", "active", "ledger")

    def test_unknown_implementation_rejected(self) -> None:
        with self.assertRaises(ValueError):
            execute_probe(self.scenario, self.action, "active", "other")

    def test_trace_envelope_tamper_rejected(self) -> None:
        trace = execute_probe(self.scenario, self.action, "active", "ledger")
        document = copy.deepcopy(trace.document)
        document["extra"] = True
        with self.assertRaises(ValueError):
            parse_probe(ProbeTrace("ledger", "active", self.action, document))

    def test_trace_oracle_tamper_rejected(self) -> None:
        trace = execute_probe(self.scenario, self.action, "active", "queue")
        document = copy.deepcopy(trace.document)
        for message in document["messages"]:
            if message["topic"] == "oracle.result":
                message["body"]["ok"] = "yes"
        with self.assertRaises(ValueError):
            parse_probe(ProbeTrace("queue", "active", self.action, document))

    def test_recovery_must_restore_broken_relation(self) -> None:
        with self.assertRaises(ValueError):
            execute_recovery(self.scenario, self.action, "fresh_state")

    def test_recovery_eventually_preserves(self) -> None:
        restored = next(iter(ACTION_BY_ID[self.action]))
        self.assertTrue(execute_recovery(self.scenario, self.action, restored).eventual_preservation)


if __name__ == "__main__":
    unittest.main()
