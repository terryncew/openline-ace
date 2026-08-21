from __future__ import annotations

import unittest

from rcdl.evaluator import evaluate
from rcdl.oracle import check_raft_safety
from rcdl.raft import (
    HOOK_SCENARIOS,
    SAFETY_CLAUSE_IDS,
    SPURIOUS_CONTROL_IDS,
    raft_candidate_clauses,
    run_intervention,
    run_scenario,
)


class RaftOracleTests(unittest.TestCase):
    def test_every_baseline_scenario_is_safe(self) -> None:
        scenarios = {"healthy", *HOOK_SCENARIOS.values()}
        for seed in range(4):
            for scenario in scenarios:
                with self.subTest(seed=seed, scenario=scenario):
                    self.assertTrue(check_raft_safety(run_scenario(scenario, seed)).passed)

    def test_safety_clause_interventions_reach_external_failure(self) -> None:
        for seed in range(4):
            for clause in raft_candidate_clauses():
                if clause.id not in SAFETY_CLAUSE_IDS:
                    continue
                with self.subTest(seed=seed, clause=clause.id):
                    self.assertFalse(
                        check_raft_safety(run_intervention(clause.hook, "active", seed)).passed
                    )

    def test_spurious_control_breaks_clause_without_external_failure(self) -> None:
        for seed in range(4):
            for clause in raft_candidate_clauses():
                if clause.id not in SPURIOUS_CONTROL_IDS:
                    continue
                with self.subTest(seed=seed, clause=clause.id):
                    trace = run_intervention(clause.hook, "active", seed)
                    self.assertFalse(evaluate(clause, trace).passed)
                    self.assertTrue(check_raft_safety(trace).passed)

    def test_every_sham_preserves_external_behavior(self) -> None:
        for clause in raft_candidate_clauses():
            with self.subTest(clause=clause.id):
                self.assertTrue(check_raft_safety(run_intervention(clause.hook, "sham", 9)).passed)

    def test_expected_safety_property_is_hit(self) -> None:
        expected = {
            "vote_once_guard": "election_safety",
            "vote_persist_guard": "election_safety",
            "vote_fresh_log_guard": "leader_completeness",
            "append_prefix_guard": "log_matching",
            "commit_majority_guard": "state_machine_safety",
            "apply_commit_guard": "state_machine_safety",
        }
        for hook, property_name in expected.items():
            report = check_raft_safety(run_intervention(hook, "active", 1))
            with self.subTest(hook=hook):
                self.assertFalse(report.properties[property_name])

    def test_oracle_ignores_intervention_label(self) -> None:
        sham = run_intervention("vote_once_guard", "sham", 5).to_dict()
        sham["events"][0]["attrs"]["arm"] = "active"
        report = check_raft_safety(type(run_scenario("healthy", 0)).from_dict(sham))
        self.assertTrue(report.passed)


if __name__ == "__main__":
    unittest.main()
