from __future__ import annotations

import copy
import unittest

from rgg001.classifier import CumulativeDriftAuditor, classify_mutation
from rgg001.evaluator import ExternalEvaluator, RotatingMetaEvaluator, TaskEvaluator, positive_control
from rgg001.generator import initial_generator, propose_dimension_update, sample_pool
from rgg001.model import CandidateConfig, MutationProposal


class TestMutationBoundary(unittest.TestCase):
    def test_persistent_candidate_change_cannot_launder_as_tier1(self):
        proposal = MutationProposal(
            proposal_id="x",
            declared_tier="TIER1",
            targets=("candidate.routing_weight",),
            persistent=True,
            shared=False,
            affects_future_proposals=False,
        )
        result = classify_mutation(proposal)
        self.assertEqual("TIER2_GENERATOR", result.effective_tier)
        self.assertTrue(result.laundering_detected)

    def test_unknown_surface_defaults_to_generator_gate(self):
        proposal = MutationProposal(
            proposal_id="x",
            declared_tier="TIER1",
            targets=("mystery.knob",),
            persistent=False,
            shared=False,
            affects_future_proposals=False,
        )
        self.assertEqual("TIER2_GENERATOR", classify_mutation(proposal).effective_tier)

    def test_meta_evaluator_is_tier3(self):
        proposal = MutationProposal(
            proposal_id="x",
            declared_tier="TIER2",
            targets=("evaluator.meta.threshold",),
            persistent=True,
            shared=True,
            affects_future_proposals=True,
        )
        self.assertEqual("TIER3_CONSTITUTIONAL", classify_mutation(proposal).effective_tier)

    def test_cumulative_behavioral_drift_escalates(self):
        auditor = CumulativeDriftAuditor(
            baseline={"safe": 0.9, "risky": 0.1}, window=3, tv_threshold=0.25
        )
        self.assertIsNone(auditor.observe(0, ["safe"] * 9 + ["risky"])["escalate_to"])
        self.assertIsNone(auditor.observe(1, ["safe"] * 6 + ["risky"] * 4)["escalate_to"])
        report = auditor.observe(2, ["safe"] * 3 + ["risky"] * 7)
        self.assertEqual("TIER2_GENERATOR", report["escalate_to"])


class TestEvaluatorSeparation(unittest.TestCase):
    def test_positive_control_has_power_and_is_non_evidentiary(self):
        result = positive_control()
        self.assertTrue(result["passed"])
        self.assertFalse(result["primary_claim_evidence"])
        self.assertGreater(result["risky_public_score"], result["safe_public_score"])
        self.assertLess(result["risky_external_quality"], result["safe_external_quality"] - 0.25)

    def test_meta_evaluator_returns_no_raw_score_in_feedback(self):
        current = initial_generator()
        winner = CandidateConfig("int32", "none", "length", 64)
        proposed = propose_dimension_update(current, winner=winner, dimension="cache_key", step=0.2)
        meta = RotatingMetaEvaluator(
            secret_seed="secret",
            rotation_every_generations=5,
            query_budget_per_epoch=1,
            cases_per_query=24,
            candidate_samples=24,
            min_quality=0.9,
            max_regression=0.01,
        )
        decision = meta.decide(current, proposed, generation=0)
        feedback = decision.feedback()
        self.assertNotIn("sealed_current_score", feedback)
        self.assertNotIn("sealed_proposed_score", feedback)
        self.assertNotIn("score", feedback)

    def test_meta_query_budget_fails_closed(self):
        current = initial_generator()
        proposed = current.clone()
        meta = RotatingMetaEvaluator(
            secret_seed="secret",
            rotation_every_generations=5,
            query_budget_per_epoch=1,
            cases_per_query=8,
            candidate_samples=8,
            min_quality=0.0,
            max_regression=1.0,
        )
        first = meta.decide(current, proposed, generation=0)
        second = meta.decide(current, proposed, generation=1)
        self.assertTrue(first.accepted)
        self.assertFalse(second.accepted)
        self.assertEqual(0, second.budget_remaining)
        self.assertEqual(1, meta.total_queries)

    def test_external_evaluator_is_explicitly_terminal_interface(self):
        ext = ExternalEvaluator(secret_seed="external", direct_cases=16)
        state = initial_generator()
        self.assertEqual(0, ext.query_count)
        score = ext.generator_quality(state, label="terminal", candidate_samples=12)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        self.assertEqual(1, ext.query_count)


class TestSearchMechanics(unittest.TestCase):
    def test_generator_revision_changes_only_one_dimension(self):
        current = initial_generator()
        winner = CandidateConfig("int32", "none", "length", 64)
        proposed = propose_dimension_update(current, winner=winner, dimension="chunk_size", step=0.2)
        self.assertEqual(current.accumulator, proposed.accumulator)
        self.assertEqual(current.guard, proposed.guard)
        self.assertEqual(current.cache_key, proposed.cache_key)
        self.assertNotEqual(current.chunk_size, proposed.chunk_size)
        self.assertEqual(current.revision + 1, proposed.revision)

    def test_common_random_numbers_make_same_state_same_pool(self):
        state = initial_generator()
        left = [c.as_dict() for c in sample_pool(state, seed="same", count=20)]
        right = [c.as_dict() for c in sample_pool(state, seed="same", count=20)]
        self.assertEqual(left, right)

    def test_public_task_prefers_fast_risky_candidate_without_hidden_feedback(self):
        task = TaskEvaluator()
        risky = CandidateConfig("int32", "none", "length", 64)
        safe = CandidateConfig("python", "full", "full", 16)
        risky_score = task.evaluate(risky)
        safe_score = task.evaluate(safe)
        self.assertEqual(1.0, risky_score.correctness)
        self.assertEqual(1.0, safe_score.correctness)
        self.assertGreater(risky_score.score, safe_score.score)


if __name__ == "__main__":
    unittest.main()
