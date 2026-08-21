from __future__ import annotations

import unittest

from rcdl.evaluator import evaluate
from rcdl.model import Clause
from rcdl.raft import raft_candidate_clauses, run_intervention, run_scenario
from rcdl.trace import Trace, TraceValidationError


class TraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = run_scenario("healthy", 0).to_dict()

    def test_round_trip(self) -> None:
        trace = Trace.from_dict(self.document)
        self.assertEqual(trace.to_dict(), self.document)

    def test_duplicate_event_id_is_rejected(self) -> None:
        self.document["events"][1]["event_id"] = self.document["events"][0]["event_id"]
        with self.assertRaises(TraceValidationError):
            Trace.from_dict(self.document)

    def test_non_increasing_step_is_rejected(self) -> None:
        self.document["events"][1]["step"] = self.document["events"][0]["step"]
        with self.assertRaises(TraceValidationError):
            Trace.from_dict(self.document)

    def test_reserved_attribute_is_rejected(self) -> None:
        self.document["events"][0]["attrs"]["node"] = "forged"
        with self.assertRaises(TraceValidationError):
            Trace.from_dict(self.document)


class EvaluatorTests(unittest.TestCase):
    @staticmethod
    def _trace(events, **metadata):
        return Trace.from_dict(
            {
                "schema": "rcdl.trace/0.1",
                "run_id": "operator-test",
                "metadata": metadata,
                "events": [
                    {
                        "event_id": f"e{index}",
                        "step": index,
                        "node": event[0],
                        "kind": event[1],
                        "attrs": event[2],
                    }
                    for index, event in enumerate(events)
                ],
            }
        )

    def test_all_candidates_hold_on_healthy_trace(self) -> None:
        trace = run_scenario("healthy", 3)
        for clause in raft_candidate_clauses():
            with self.subTest(clause=clause.id):
                result = evaluate(clause, trace)
                self.assertTrue(result.passed)
                self.assertGreater(result.support_count, 0)

    def test_targeted_active_arm_violates_each_clause(self) -> None:
        for clause in raft_candidate_clauses():
            with self.subTest(clause=clause.id):
                result = evaluate(clause, run_intervention(clause.hook, "active", 7))
                self.assertFalse(result.passed)
                self.assertGreater(result.violation_count, 0)

    def test_targeted_sham_arm_preserves_each_clause(self) -> None:
        for clause in raft_candidate_clauses():
            with self.subTest(clause=clause.id):
                result = evaluate(clause, run_intervention(clause.hook, "sham", 7))
                self.assertTrue(result.passed)

    def test_zero_trigger_clause_does_not_earn_support(self) -> None:
        document = raft_candidate_clauses()[1].to_dict()
        document["id"] = "test.no_trigger"
        document["trigger"]["event"] = "never_happens"
        result = evaluate(Clause.from_dict(document), run_scenario("healthy", 0))
        self.assertTrue(result.passed)
        self.assertEqual(result.trigger_count, 0)
        self.assertEqual(result.support_count, 0)

    def test_precedes_without_detects_intervening_mutation(self) -> None:
        clause = Clause.from_dict(
            {
                "schema": "rcdl.clause/0.1",
                "id": "test.persist_without_restart",
                "kind": "order",
                "trigger": {"event": "vote_reply", "where": {"granted": True}},
                "require": {
                    "op": "precedes_without",
                    "event": "durable_write",
                    "joins": {"node": "node", "term": "term"},
                    "blocker": {
                        "event": "restart",
                        "joins": {"node": "node"},
                    },
                },
                "intervention": {
                    "hook": "persistence_guard",
                    "active": "bypass_guard",
                    "sham": "metadata_noop",
                    "energy": 1,
                },
            }
        )
        trace = self._trace(
            [
                ("n0", "durable_write", {"term": 1}),
                ("n0", "restart", {}),
                ("n0", "vote_reply", {"term": 1, "granted": True}),
            ]
        )
        result = evaluate(clause, trace)
        self.assertFalse(result.passed)
        self.assertEqual(result.violations[0]["reason"], "intervening_blocker")

    def test_eventually_within_is_bounded_and_assumption_gated(self) -> None:
        clause = Clause.from_dict(
            {
                "schema": "rcdl.clause/0.1",
                "id": "test.reply_within_two_steps",
                "kind": "progress",
                "trigger": {"event": "request"},
                "require": {
                    "op": "eventually_within",
                    "event": "reply",
                    "joins": {"request_id": "request_id"},
                    "horizon": 2,
                    "assumptions": ["fair_delivery"],
                },
                "intervention": {
                    "hook": "delivery_guard",
                    "active": "drop_message",
                    "sham": "metadata_noop",
                    "energy": 1,
                },
            }
        )
        passing = self._trace(
            [
                ("n0", "request", {"request_id": "r1"}),
                ("system", "tick", {}),
                ("n1", "reply", {"request_id": "r1"}),
            ],
            fair_delivery=True,
        )
        failing = self._trace(
            [("n0", "request", {"request_id": "r1"})], fair_delivery=True
        )
        gated = self._trace(
            [("n0", "request", {"request_id": "r1"})], fair_delivery=False
        )
        self.assertTrue(evaluate(clause, passing).passed)
        self.assertFalse(evaluate(clause, failing).passed)
        gated_result = evaluate(clause, gated)
        self.assertTrue(gated_result.passed)
        self.assertEqual(gated_result.support_count, 0)


if __name__ == "__main__":
    unittest.main()
