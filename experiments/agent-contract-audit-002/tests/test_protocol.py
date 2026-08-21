from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aca002.blind import make_compiler_packet, make_proposer_packet
from aca002.compiler import compile_candidates
from aca002.fixture import conformance_results
from aca002.grade import grade_external
from aca002.ingest import validate_result, verify_against_schedule
from aca002.pin import verify_a001_pin
from aca002.replay import replay_verifier
from aca002.schedule import build_schedule
from aca002.schemas import assert_blind
from aca002.task import observation_for

ROOT = Path(__file__).resolve().parents[1]

PROPOSED = [
    {"candidate_id":"c1","text":"value fresh","scope":"ticket","relation":"freshness","evidence_refs":["x"]},
    {"candidate_id":"c2","text":"marker present","scope":"ticket","relation":"presence","evidence_refs":["y"]}
]
MAP = [
    {"candidate_id":"c1","surface_id":"ticket.token_freshness"},
    {"candidate_id":"c2","surface_id":"ticket.audit_marker_presence"}
]

class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT / "fixtures/surface_catalog.json").read_text())
        cls.tasks = json.loads((ROOT / "fixtures/tasks.json").read_text())["tasks"]
        cls.candidates = compile_candidates(PROPOSED, MAP, cls.catalog)

    def test_a001_pin(self):
        observed = verify_a001_pin()
        self.assertEqual(set(observed), {"audit.py", "model.py", "stats.py"})

    def test_blind_packet_rejects_hidden_key(self):
        with self.assertRaises(ValueError):
            assert_blind({"ground_truth": "x"})

    def test_proposer_packet_is_blind(self):
        packet = make_proposer_packet([{
            "trace_id":"t1", "task_id":"ticket-01", "events":["read_ticket"],
            "tool_observation":{"value":"X","marker":"M","padding":"P"}, "final_success":True
        }])
        assert_blind(packet)
        encoded = json.dumps(packet)
        self.assertNotIn("current_token", encoded)
        self.assertNotIn("stale_token", encoded)
        self.assertNotIn("verifier_success", encoded)

    def test_compiler_packet_is_blind(self):
        packet = make_compiler_packet(PROPOSED, self.catalog)
        assert_blind(packet)
        self.assertEqual(len(packet["surfaces"]), 3)

    def test_deterministic_compiler(self):
        got = self.candidates
        self.assertEqual(got[0]["interventions"]["active"]["op"], "ticket_token_stale")
        self.assertEqual(got[1]["interventions"]["active"]["op"], "audit_marker_neutralize")

    def test_surface_mutations_preserve_lengths(self):
        t = self.tasks[0]
        base = observation_for(t, "none")
        marker = observation_for(t, "audit_marker_neutralize")
        padding = observation_for(t, "padding_substitute")
        self.assertEqual(len(base["value"]), len(base["marker"]))
        self.assertEqual(len(base["value"]), len(base["padding"]))
        self.assertEqual(len(base["marker"]), len(marker["marker"]))
        self.assertEqual(len(base["padding"]), len(padding["padding"]))

    def test_schedule_has_four_arms_and_64_pairs(self):
        rows = build_schedule(self.candidates[:1], self.tasks, pairs=64)
        self.assertEqual(len(rows), 256)
        self.assertEqual({r["arm"] for r in rows}, {"baseline","active","sham","restoration"})

    def test_schedule_rejects_underpowered_run(self):
        with self.assertRaises(ValueError):
            build_schedule(self.candidates, self.tasks, pairs=63)

    def test_conformance_separates_dependency_and_ritual(self):
        schedule, rows = conformance_results(self.candidates, self.tasks)
        verify_against_schedule(rows, schedule)
        grade = grade_external(self.candidates, rows)
        standings = {g["candidate_id"]: g["standing"] for g in grade["grades"]}
        self.assertEqual(standings["c1"], "SUPPORTED")
        self.assertEqual(standings["c2"], "REJECTED_RITUAL")

    def test_independent_replay(self):
        _, rows = conformance_results(self.candidates, self.tasks)
        self.assertTrue(replay_verifier(rows, self.tasks)["verified"])

    def test_replay_detects_verifier_lie(self):
        _, rows = conformance_results(self.candidates, self.tasks)
        rows[0] = dict(rows[0])
        rows[0]["verifier"] = dict(rows[0]["verifier"])
        rows[0]["verifier"]["success"] = not rows[0]["verifier"]["success"]
        self.assertFalse(replay_verifier(rows, self.tasks)["verified"])

    def test_ingest_rejects_duplicate_schedule_result(self):
        schedule, rows = conformance_results(self.candidates[:1], self.tasks)
        with self.assertRaises(ValueError):
            verify_against_schedule(rows + [rows[0]], schedule)

    def test_result_schema_requires_provider(self):
        _, rows = conformance_results(self.candidates[:1], self.tasks)
        value = dict(rows[0]); value.pop("provider")
        with self.assertRaises(ValueError):
            validate_result(value)

    def test_diagnostic_status_does_not_change_standing(self):
        _, rows = conformance_results(self.candidates, self.tasks)
        g1 = grade_external(self.candidates, rows)
        rows2 = [dict(r) for r in rows]
        rows2[0]["runner_status"] = "wrapper-blocked-display-only"
        g2 = grade_external(self.candidates, rows2)
        self.assertEqual([g["standing"] for g in g1["grades"]], [g["standing"] for g in g2["grades"]])

if __name__ == "__main__":
    unittest.main()
