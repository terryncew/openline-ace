from __future__ import annotations

import unittest
import inspect

from envharness import Action, Rules

from rcdl006.environment import CodeRepairEnv, stack_proposal
from rcdl006.execution import execute_queries, run_arm
import rcdl006.execution as execution_module
from rcdl006.fixtures import development_tasks, heldout_tasks, load_fixtures
from rcdl006.model import Split, Standing


class ExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = load_fixtures()
        cls.task = development_tasks()[0]

    def proposal(self, standing: Standing, split: Split = Split.DEVELOPMENT):
        return next(
            item for item in self.fixtures.by_split(split)
            if self.fixtures.oracle[item.proposal_id].standing is standing
        )

    def test_original_verifier_does_not_require_tests(self) -> None:
        env = CodeRepairEnv(self.task, self.task.correct_patch)
        env.reset()
        env.step(Action(name="submit"))
        self.assertTrue(env.evaluate().success)

    def test_executor_does_not_import_or_consume_oracle_labels(self) -> None:
        source = inspect.getsource(execution_module)
        self.assertNotIn("OracleEntry", source)
        self.assertNotIn("oracle.standing", source)

    def test_wrapper_can_manufacture_submission_requirement(self) -> None:
        proposal = self.proposal(Standing.REJECTED_IMPOSED)
        env = stack_proposal(CodeRepairEnv(self.task, self.task.correct_patch), proposal, "active")
        self.assertIsInstance(env, Rules)
        env.reset()
        env.step(Action(name="submit"))
        self.assertFalse(env.evaluate().success)
        self.assertTrue(env.evaluate().metrics["artifact_valid"])

    def test_native_signature_breaks_artifact(self) -> None:
        proposal = self.proposal(Standing.SUPPORTED_NATIVE)
        transcript = execute_queries(proposal, self.task, "direct-v1")
        self.assertEqual(transcript.signature(), (False, False, True, True, 4))

    def test_imposed_signature_preserves_artifact(self) -> None:
        proposal = self.proposal(Standing.REJECTED_IMPOSED)
        transcript = execute_queries(proposal, self.task, "direct-v1")
        self.assertEqual(transcript.signature(), (False, True, True, True, 2))

    def test_nuisance_signature_preserves_behavior(self) -> None:
        proposal = self.proposal(Standing.REJECTED_NUISANCE)
        transcript = execute_queries(proposal, self.task, "direct-v1")
        self.assertEqual(transcript.signature(), (True, True, True, True, 0))

    def test_sham_energy_is_matched(self) -> None:
        for proposal in self.fixtures.proposals:
            task = self.task if proposal.split is Split.DEVELOPMENT else heldout_tasks()[0]
            agent = "direct-v1" if proposal.split is Split.DEVELOPMENT else "ledger-v2"
            transcript = execute_queries(proposal, task, agent)
            self.assertEqual(transcript.active.energy, transcript.sham.energy)
            self.assertTrue(transcript.sham.external_success)

    def test_heldout_agents_transport_signatures(self) -> None:
        task = heldout_tasks()[0]
        for proposal in self.fixtures.by_split(Split.EVALUATION):
            left = execute_queries(proposal, task, "ledger-v2")
            right = execute_queries(proposal, task, "queue-v2")
            self.assertEqual(left.signature(), right.signature())

    def test_trace_replay_is_deterministic(self) -> None:
        proposal = self.proposal(Standing.SUPPORTED_NATIVE)
        left = run_arm(proposal, self.task, "direct-v1", "active")
        right = run_arm(proposal, self.task, "direct-v1", "active")
        self.assertEqual(left.trace_digest, right.trace_digest)

    def test_base_environment_save_restore_roundtrip(self) -> None:
        env = CodeRepairEnv(self.task, self.task.alternate_patch)
        env.reset()
        env.step(Action(name="apply_patch", kwargs={"patch": self.task.correct_patch}))
        restored = CodeRepairEnv.from_state(env.save_state())
        self.assertEqual(restored.get_env_state(), env.get_env_state())

    def test_unknown_agent_is_rejected(self) -> None:
        proposal = self.proposal(Standing.REJECTED_NUISANCE)
        with self.assertRaisesRegex(ValueError, "unknown agent"):
            run_arm(proposal, self.task, "mystery", "active")


if __name__ == "__main__":
    unittest.main()
