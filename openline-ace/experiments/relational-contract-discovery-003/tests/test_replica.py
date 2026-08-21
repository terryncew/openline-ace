from __future__ import annotations

import unittest

from rcdl.evaluator import evaluate

from rcdl003.contracts import (
    PLANNER_NOTE_HOOK,
    SPURIOUS_CONTROL_IDS,
    TARGET_CLAUSE_IDS,
    frozen_clauses,
)
from rcdl003.oracle import check_external_behavior
from rcdl003.replica import run_batch, run_pair


class ReplicaTests(unittest.TestCase):
    def test_target_active_arms_fail_clause_and_oracle(self) -> None:
        for clause in frozen_clauses():
            if clause.id not in TARGET_CLAUSE_IDS:
                continue
            with self.subTest(clause=clause.id):
                run = run_pair(clause.hook, "active", 7)
                self.assertFalse(evaluate(clause, run.trace).passed)
                self.assertFalse(check_external_behavior(run.outcome).passed)

    def test_all_shams_preserve_clause_and_oracle(self) -> None:
        for clause in frozen_clauses():
            with self.subTest(clause=clause.id):
                run = run_pair(clause.hook, "sham", 11)
                self.assertTrue(evaluate(clause, run.trace).passed)
                self.assertTrue(check_external_behavior(run.outcome).passed)

    def test_spurious_control_is_causally_rejected(self) -> None:
        clause = next(item for item in frozen_clauses() if item.id in SPURIOUS_CONTROL_IDS)
        run = run_pair(clause.hook, "active", 13)
        self.assertFalse(evaluate(clause, run.trace).passed)
        self.assertTrue(check_external_behavior(run.outcome).passed)

    def test_active_and_sham_event_counts_are_matched(self) -> None:
        for clause in frozen_clauses():
            active = run_pair(clause.hook, "active", 17)
            sham = run_pair(clause.hook, "sham", 17)
            self.assertEqual(len(active.trace.events), len(sham.trace.events))
            self.assertEqual(
                sum(event.kind == "mutation_marker" for event in active.trace.events),
                1,
            )
            self.assertEqual(
                sum(event.kind == "mutation_marker" for event in sham.trace.events),
                1,
            )

    def test_trace_withholds_intervention_target_and_arm(self) -> None:
        run = run_pair(PLANNER_NOTE_HOOK, "active", 19)
        for event in run.trace.events:
            self.assertNotIn("hook", event.attrs)
            self.assertNotIn("arm", event.attrs)
            self.assertNotIn("oracle_passed", event.attrs)

    def test_unseen_target_combination_fails(self) -> None:
        hooks = tuple(
            clause.hook for clause in frozen_clauses() if clause.id in TARGET_CLAUSE_IDS
        )
        active = run_batch(hooks, active_hooks=hooks, seed=23)
        sham = run_batch(hooks, active_hooks=(), seed=23)
        self.assertFalse(check_external_behavior(active.outcome).passed)
        self.assertTrue(check_external_behavior(sham.outcome).passed)
        self.assertEqual(len(active.trace.events), len(sham.trace.events))

    def test_spurious_only_batch_preserves_behavior(self) -> None:
        run = run_batch((PLANNER_NOTE_HOOK,), active_hooks=(PLANNER_NOTE_HOOK,), seed=29)
        self.assertTrue(check_external_behavior(run.outcome).passed)

    def test_recovery_active_misses_declared_horizon(self) -> None:
        clause = next(item for item in frozen_clauses() if item.id == "workflow.recovery_requires_fresh_observation")
        run = run_pair(clause.hook, "active", 31)
        job = run.outcome.jobs[0]
        self.assertGreater(job.fresh_observation_step, job.recovery_deadline)
        self.assertFalse(evaluate(clause, run.trace).passed)

    def test_invalid_batch_arguments_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            run_batch((), active_hooks=(), seed=0)
        with self.assertRaises(ValueError):
            run_batch((PLANNER_NOTE_HOOK,), active_hooks=("unknown",), seed=0)
        with self.assertRaises(ValueError):
            run_pair(PLANNER_NOTE_HOOK, "control", 0)


if __name__ == "__main__":
    unittest.main()
