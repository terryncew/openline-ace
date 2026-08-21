from __future__ import annotations

import unittest

from rcdl006.execution import execute_queries
from rcdl006.fixtures import development_tasks, load_fixtures
from rcdl006.model import EpisodeOutcome, Energy, QueryTranscript, Split, Standing
from rcdl006.policies import policy_boundary, symbolic_decision, train_learned_policy


def outcome(arm: str, success: bool, artifact: bool, horizon: int | None = None) -> EpisodeOutcome:
    return EpisodeOutcome(arm, success, artifact, success, 1, horizon, "0" * 64, Energy(1, 1, 64, 0))


class PolicyTests(unittest.TestCase):
    def test_symbolic_native_decision(self) -> None:
        transcript = QueryTranscript(outcome("active", False, False), outcome("sham", True, True), outcome("restoration", True, True, 4))
        self.assertIs(symbolic_decision(transcript).standing, Standing.SUPPORTED_NATIVE)

    def test_symbolic_imposed_decision(self) -> None:
        transcript = QueryTranscript(outcome("active", False, True), outcome("sham", True, True), outcome("restoration", True, True, 2))
        self.assertIs(symbolic_decision(transcript).standing, Standing.REJECTED_IMPOSED)

    def test_symbolic_nuisance_decision(self) -> None:
        transcript = QueryTranscript(outcome("active", True, True), outcome("sham", True, True), outcome("restoration", True, True, 0))
        self.assertIs(symbolic_decision(transcript).standing, Standing.REJECTED_NUISANCE)

    def test_failed_sham_is_invalid(self) -> None:
        transcript = QueryTranscript(outcome("active", False, False), outcome("sham", False, True), outcome("restoration", True, True, 4))
        self.assertIs(symbolic_decision(transcript).standing, Standing.INVALID)

    def test_learned_policy_learns_only_development_signatures(self) -> None:
        fixtures = load_fixtures()
        task = development_tasks()[0]
        examples = []
        for proposal in fixtures.by_split(Split.DEVELOPMENT):
            oracle = fixtures.oracle[proposal.proposal_id]
            examples.append((execute_queries(proposal, task, "direct-v1"), oracle.standing))
        learned = train_learned_policy(examples)
        self.assertEqual(len(learned.table), 3)

    def test_incomplete_training_surface_is_rejected(self) -> None:
        transcript = QueryTranscript(outcome("active", True, True), outcome("sham", True, True), outcome("restoration", True, True, 0))
        with self.assertRaisesRegex(ValueError, "incomplete"):
            train_learned_policy([(transcript, Standing.REJECTED_NUISANCE)])

    def test_policy_boundary_denies_oracle_and_id_access(self) -> None:
        boundary = policy_boundary()
        self.assertFalse(boundary["learned_oracle_access"])
        self.assertFalse(boundary["learned_proposal_id_access"])
        self.assertTrue(boundary["equal_query_budget"])


if __name__ == "__main__":
    unittest.main()
