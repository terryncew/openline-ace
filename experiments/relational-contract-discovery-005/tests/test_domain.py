from __future__ import annotations

import unittest

from rcdl005.domain import (
    ACTIONS,
    ACTION_IDS,
    HYPOTHESIS_BY_ID,
    HYPOTHESES,
    OBSERVABLE_CLASSES,
    behavior_preserved,
    class_members,
    final_scenarios,
    minimal_failure_sets,
    signature,
    signature_for_class,
    verify_domain,
)


class DomainTests(unittest.TestCase):
    def test_domain_closure(self) -> None:
        self.assertTrue(verify_domain()["valid"])

    def test_action_vocabulary_is_unique(self) -> None:
        self.assertEqual(len(ACTIONS), 10)
        self.assertEqual(len(set(ACTION_IDS)), 10)

    def test_baseline_preserves_every_hypothesis(self) -> None:
        for hypothesis in HYPOTHESES:
            self.assertTrue(behavior_preserved(hypothesis.family, ()))

    def test_observable_classes_have_unique_signatures(self) -> None:
        signatures = [signature_for_class(item) for item in OBSERVABLE_CLASSES]
        self.assertEqual(len(signatures), len(set(signatures)))

    def test_non_identifiable_twins_match_in_regime(self) -> None:
        left, right = class_members("class-03")
        self.assertEqual(signature(HYPOTHESIS_BY_ID[left]), signature(HYPOTHESIS_BY_ID[right]))

    def test_non_identifiable_twins_differ_outside_regime(self) -> None:
        left, right = (HYPOTHESIS_BY_ID[item] for item in class_members("class-03"))
        triples = (
            ("provenance", "review", "ordering"),
            ("provenance", "review", "fresh_state"),
            ("provenance", "ordering", "fresh_state"),
            ("review", "ordering", "fresh_state"),
        )
        self.assertTrue(
            any(
                behavior_preserved(left.family, item)
                != behavior_preserved(right.family, item)
                for item in triples
            )
        )

    def test_final_scenarios_are_balanced(self) -> None:
        rows = final_scenarios()
        self.assertEqual(len(rows), 256)
        self.assertEqual(
            {sum(row.observable_class == item for row in rows) for item in OBSERVABLE_CLASSES},
            {32},
        )

    def test_minimal_failure_sets_prune_supersets(self) -> None:
        hypothesis = HYPOTHESIS_BY_ID["provenance_and_review"]
        cuts = minimal_failure_sets(signature(hypothesis))
        self.assertEqual(cuts, (("provenance",), ("review",)))

    def test_unknown_relation_rejected(self) -> None:
        with self.assertRaises(ValueError):
            behavior_preserved(HYPOTHESES[0].family, ("unknown",))


if __name__ == "__main__":
    unittest.main()

