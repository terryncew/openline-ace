from __future__ import annotations

import unittest

from rcdl007.arena import EVALUATION_FAULTS, passive_observation, query_fn, standing_for_faults
from rcdl007.model import Scenario
from rcdl007.policies import BUDGET, policy_boundary, symbolic_decide, train_learned_policy


class PolicyTests(unittest.TestCase):
    def test_boundary_excludes_post_adjudication_features(self) -> None:
        boundary = policy_boundary()
        forbidden = set(boundary["forbidden_eval_inputs"])
        self.assertIn("artifact_valid", forbidden)
        self.assertIn("standing label", forbidden)
        self.assertIn("recovery horizon", forbidden)
        self.assertEqual(boundary["policy_authority"], "NONE")

    def test_learned_history_is_action_complete(self) -> None:
        learned = train_learned_policy()
        self.assertEqual(len(learned.records), 7)
        lengths = {len(record.responses) for record in learned.records}
        self.assertEqual(lengths, {10})

    def test_both_policies_resolve_every_held_out_family_under_budget(self) -> None:
        learned = train_learned_policy()
        for index, faults in enumerate(EVALUATION_FAULTS):
            scenario = Scenario(f"policy-{index:02d}", faults, 400 + index)
            passive = passive_observation(scenario, "ledger-v3")
            expected = standing_for_faults(faults)
            symbolic = symbolic_decide(passive, query_fn(scenario, "ledger-v3"))
            learned_decision = learned.decide(passive, query_fn(scenario, "ledger-v3"))
            self.assertEqual(symbolic.standing, expected)
            self.assertEqual(learned_decision.standing, expected)
            self.assertLessEqual(len(symbolic.queries), BUDGET)
            self.assertLessEqual(len(learned_decision.queries), BUDGET)

    def test_query_sequences_match_in_frozen_pilot(self) -> None:
        learned = train_learned_policy()
        for index, faults in enumerate(EVALUATION_FAULTS):
            scenario = Scenario(f"seq-{index:02d}", faults, 800 + index)
            passive = passive_observation(scenario, "queue-v3")
            symbolic = symbolic_decide(passive, query_fn(scenario, "queue-v3"))
            learned_decision = learned.decide(passive, query_fn(scenario, "queue-v3"))
            self.assertEqual(
                [event.probe_id for event in symbolic.queries],
                [event.probe_id for event in learned_decision.queries],
            )


if __name__ == "__main__":
    unittest.main()
