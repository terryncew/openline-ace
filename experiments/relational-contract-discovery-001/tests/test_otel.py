from __future__ import annotations

import unittest

from rcdl.evaluator import evaluate
from rcdl.oracle import check_raft_safety
from rcdl.otel import OTelAdapterError, trace_from_otlp, trace_to_otlp
from rcdl.raft import raft_candidate_clauses, run_intervention, run_scenario


class OTelAdapterTests(unittest.TestCase):
    def test_healthy_trace_round_trip_preserves_all_clause_results(self) -> None:
        source = run_scenario("healthy", 4)
        observed = trace_from_otlp(trace_to_otlp(source))
        self.assertEqual(observed.run_id, source.run_id)
        self.assertEqual(observed.metadata, source.metadata)
        self.assertEqual(len(observed.events), len(source.events))
        for clause in raft_candidate_clauses():
            with self.subTest(clause=clause.id):
                left = evaluate(clause, source)
                right = evaluate(clause, observed)
                self.assertEqual(
                    (left.passed, left.trigger_count, left.support_count),
                    (right.passed, right.trigger_count, right.support_count),
                )
        self.assertTrue(check_raft_safety(observed).passed)

    def test_active_failure_survives_otel_normalization(self) -> None:
        clause = raft_candidate_clauses()[0]
        source = run_intervention(clause.hook, "active", 4)
        observed = trace_from_otlp(trace_to_otlp(source))
        self.assertFalse(evaluate(clause, observed).passed)
        self.assertFalse(check_raft_safety(observed).passed)

    def test_duplicate_attribute_is_rejected(self) -> None:
        document = trace_to_otlp(run_scenario("healthy", 0))
        span = document["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        span["attributes"].append(dict(span["attributes"][0]))
        with self.assertRaises(OTelAdapterError):
            trace_from_otlp(document)

    def test_unsupported_array_attribute_is_rejected(self) -> None:
        document = trace_to_otlp(run_scenario("healthy", 0))
        span = document["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        span["attributes"].append(
            {"key": "rcdl.attr.bad", "value": {"arrayValue": {"values": []}}}
        )
        with self.assertRaises(OTelAdapterError):
            trace_from_otlp(document)


if __name__ == "__main__":
    unittest.main()
