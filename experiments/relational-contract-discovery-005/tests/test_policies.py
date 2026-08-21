from __future__ import annotations

import copy
import unittest

from rcdl005.domain import ACTION_IDS, OBSERVABLE_CLASSES, signature_for_class
from rcdl005.policies import (
    ActivePolicy,
    learned_candidates,
    load_historical_interventions,
    make_learned_policy,
    make_symbolic_policy,
    policy_boundary,
    symbolic_candidates,
)


class PolicyTests(unittest.TestCase):
    def test_policy_boundary_is_equal(self) -> None:
        self.assertTrue(policy_boundary()["same_outcome_support"])

    def test_historical_corpus_has_no_sham_failure(self) -> None:
        records = load_historical_interventions()
        self.assertTrue(all(record["sham_failed"] is False for record in records))

    def test_learned_policy_clusters_non_identifiable_twins(self) -> None:
        candidates = learned_candidates(load_historical_interventions())
        self.assertEqual(len(candidates), 8)
        self.assertEqual(sorted(item.structural_multiplicity for item in candidates), [1] * 7 + [2])

    def test_symbolic_and_learned_support_match(self) -> None:
        symbolic = {item.signature for item in symbolic_candidates()}
        learned = {item.signature for item in learned_candidates(load_historical_interventions())}
        self.assertEqual(symbolic, learned)

    def test_each_class_resolves_within_budget(self) -> None:
        for class_id in OBSERVABLE_CLASSES:
            for factory in (make_symbolic_policy, make_learned_policy):
                policy = factory()
                expected = signature_for_class(class_id)
                for _ in range(4):
                    action = policy.choose_action()
                    if action is None:
                        break
                    policy.observe(action, expected[ACTION_IDS.index(action)], False)
                self.assertEqual(policy.finish().signature, expected)

    def test_all_classes_resolve_in_three_queries(self) -> None:
        for class_id in OBSERVABLE_CLASSES:
            policy = make_symbolic_policy()
            expected = signature_for_class(class_id)
            while (action := policy.choose_action()) is not None:
                policy.observe(action, expected[ACTION_IDS.index(action)], False)
            self.assertEqual(len(policy.finish().queries), 3)

    def test_sham_failure_rejected(self) -> None:
        policy = make_symbolic_policy()
        action = policy.choose_action()
        self.assertIsNotNone(action)
        with self.assertRaises(ValueError):
            policy.observe(str(action), False, True)

    def test_repeated_action_rejected(self) -> None:
        policy = make_symbolic_policy()
        action = policy.choose_action()
        self.assertIsNotNone(action)
        policy.observe(str(action), False, False)
        with self.assertRaises(ValueError):
            policy.observe(str(action), False, False)

    def test_eliminating_version_space_rejected(self) -> None:
        candidate = symbolic_candidates()[0]
        policy = ActivePolicy("test", (candidate, symbolic_candidates()[1]))
        action = next(
            action_id
            for action_id in ACTION_IDS
            if candidate.outcome(action_id) == symbolic_candidates()[1].outcome(action_id)
        )
        with self.assertRaises(ValueError):
            policy.observe(action, not candidate.outcome(action), False)

    def test_tampered_history_rejected(self) -> None:
        records = [copy.deepcopy(item) for item in load_historical_interventions()]
        records[0]["sham_failed"] = True
        with self.assertRaises(ValueError):
            learned_candidates(records)


if __name__ == "__main__":
    unittest.main()
