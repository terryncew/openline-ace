from __future__ import annotations

import unittest

from rcdl.canonical import canonical_digest
from rcdl.evaluator import evaluate

from rcdl002.oracle import check_workflow_behavior
from rcdl002.workflow import (
    ALL_HOOKS,
    HOOK_SCENARIOS,
    RECOVERY_HORIZON,
    SPURIOUS_CONTROL_IDS,
    TARGET_CLAUSE_IDS,
    RECOVERY_OBSERVATION_HOOK,
    build_task,
    run_intervention,
    run_scenario,
    workflow_candidate_clauses,
)


class WorkflowSubstrateTests(unittest.TestCase):
    def test_every_guarded_baseline_satisfies_external_oracle(self) -> None:
        scenarios = {"healthy", *HOOK_SCENARIOS.values()}
        for seed in range(4):
            for scenario in scenarios:
                with self.subTest(seed=seed, scenario=scenario):
                    report = check_workflow_behavior(run_scenario(scenario, seed).outcome)
                    self.assertTrue(report.passed)

    def test_each_target_active_arm_breaks_clause_and_external_behavior(self) -> None:
        for seed in range(4):
            for clause in workflow_candidate_clauses():
                if clause.id not in TARGET_CLAUSE_IDS:
                    continue
                with self.subTest(seed=seed, clause=clause.id):
                    run = run_intervention(clause.hook, "active", seed)
                    self.assertFalse(evaluate(clause, run.trace).passed)
                    self.assertFalse(check_workflow_behavior(run.outcome).passed)

    def test_spurious_active_arm_breaks_clause_without_external_failure(self) -> None:
        for clause in workflow_candidate_clauses():
            if clause.id not in SPURIOUS_CONTROL_IDS:
                continue
            run = run_intervention(clause.hook, "active", 11)
            self.assertFalse(evaluate(clause, run.trace).passed)
            self.assertTrue(check_workflow_behavior(run.outcome).passed)

    def test_every_sham_preserves_clause_and_external_behavior(self) -> None:
        for clause in workflow_candidate_clauses():
            with self.subTest(clause=clause.id):
                run = run_intervention(clause.hook, "sham", 13)
                self.assertTrue(evaluate(clause, run.trace).passed)
                self.assertTrue(check_workflow_behavior(run.outcome).passed)

    def test_recovery_deadline_is_hit_only_by_active_arm(self) -> None:
        active = run_intervention(RECOVERY_OBSERVATION_HOOK, "active", 17)
        sham = run_intervention(RECOVERY_OBSERVATION_HOOK, "sham", 17)
        self.assertEqual(
            active.outcome.recovery_deadline,
            active.outcome.failure_step + RECOVERY_HORIZON,
        )
        self.assertGreater(
            active.outcome.fresh_observation_step,
            active.outcome.recovery_deadline,
        )
        self.assertLessEqual(
            sham.outcome.fresh_observation_step,
            sham.outcome.recovery_deadline,
        )
        self.assertFalse(
            check_workflow_behavior(active.outcome).properties["bounded_recovery"]
        )
        self.assertTrue(
            check_workflow_behavior(sham.outcome).properties["bounded_recovery"]
        )

    def test_oracle_labels_are_absent_from_discovery_trace(self) -> None:
        forbidden = {
            "correct_release_decision",
            "hidden_tests",
            "authorized_side_effects",
            "evidence_current",
            "approval_safety",
            "bounded_recovery",
            "oracle_passed",
            "failed_properties",
        }
        for scenario in {"healthy", *HOOK_SCENARIOS.values()}:
            document = run_scenario(scenario, 19).trace.to_dict()
            stack: list[object] = [document]
            observed_keys: set[str] = set()
            while stack:
                value = stack.pop()
                if isinstance(value, dict):
                    observed_keys.update(value)
                    stack.extend(value.values())
                elif isinstance(value, list):
                    stack.extend(value)
            self.assertTrue(forbidden.isdisjoint(observed_keys), scenario)

    def test_same_seed_is_byte_deterministic(self) -> None:
        first = run_scenario("recovery", 23)
        second = run_scenario("recovery", 23)
        self.assertEqual(first.trace.to_dict(), second.trace.to_dict())
        self.assertEqual(first.outcome, second.outcome)
        self.assertEqual(
            canonical_digest(first.trace.to_dict()),
            canonical_digest(second.trace.to_dict()),
        )

    def test_each_arm_records_one_structural_energy_unit(self) -> None:
        for hook in ALL_HOOKS:
            for arm in ("active", "sham"):
                with self.subTest(hook=hook, arm=arm):
                    run = run_intervention(hook, arm, 29)
                    interventions = [
                        event for event in run.trace.events if event.kind == "intervention"
                    ]
                    self.assertEqual(len(interventions), 1)
                    self.assertEqual(interventions[0].attrs["energy"], 1)
                    self.assertEqual(interventions[0].attrs["hook"], hook)
                    self.assertEqual(interventions[0].attrs["arm"], arm)

    def test_invalid_seed_scenario_hook_and_arm_fail_closed(self) -> None:
        for seed in (-1, True, 1.5):
            with self.subTest(seed=seed):
                with self.assertRaises(ValueError):
                    build_task(seed)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            run_scenario("unknown", 0)
        with self.assertRaises(ValueError):
            run_scenario("healthy", 0, enabled_hooks={"unknown"})
        with self.assertRaises(ValueError):
            run_intervention("unknown", "active", 0)
        with self.assertRaises(ValueError):
            run_intervention(next(iter(ALL_HOOKS)), "unknown", 0)


if __name__ == "__main__":
    unittest.main()
