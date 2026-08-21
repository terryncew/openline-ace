from __future__ import annotations

import unittest

from rcdl004.models import (
    FeatureRow,
    HighPrecisionRelationalRuleSet,
    MarginPerceptron,
    RelationalDecisionTree,
)


ROWS = (
    FeatureRow({"a": 1, "b": 1}, True),
    FeatureRow({"a": 1, "c": 1}, True),
    FeatureRow({"b": 1}, False),
    FeatureRow({"c": 1}, False),
)


class ModelTests(unittest.TestCase):
    def test_tree_learns_separable_rows(self) -> None:
        model = RelationalDecisionTree(max_depth=3, min_leaf=1).fit(ROWS)
        self.assertEqual([model.predict(row.features) for row in ROWS], [row.failed for row in ROWS])

    def test_perceptron_is_deterministic(self) -> None:
        left = MarginPerceptron(epochs=8).fit(ROWS)
        right = MarginPerceptron(epochs=8).fit(ROWS)
        self.assertEqual(left.weights, right.weights)
        self.assertEqual(left.bias, right.bias)

    def test_rule_set_learns_zero_negative_support_conjunction(self) -> None:
        model = HighPrecisionRelationalRuleSet(min_support=2).fit(ROWS)
        self.assertTrue(model.predict({"a": 1, "b": 1}))
        self.assertFalse(model.predict({"b": 1}))
        self.assertEqual(model.covered_positive_examples, 2)

    def test_models_require_both_classes(self) -> None:
        one_class = (FeatureRow({"a": 1}, True), FeatureRow({"b": 1}, True))
        with self.assertRaises(ValueError):
            RelationalDecisionTree(max_depth=2, min_leaf=1).fit(one_class)
        with self.assertRaises(ValueError):
            MarginPerceptron(epochs=2).fit(one_class)
        with self.assertRaises(ValueError):
            HighPrecisionRelationalRuleSet(min_support=2).fit(one_class)


if __name__ == "__main__":
    unittest.main()

