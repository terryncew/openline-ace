"""Deterministic learned classifiers for generic relational trace features."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from typing import Iterable


@dataclass(frozen=True)
class FeatureRow:
    features: dict[str, int]
    failed: bool


@dataclass(frozen=True)
class TreeNode:
    prediction: bool
    feature: str | None = None
    absent: "TreeNode | None" = None
    present: "TreeNode | None" = None


class RelationalDecisionTree:
    """A bounded CART-style tree over generic feature presence."""

    def __init__(self, *, max_depth: int, min_leaf: int) -> None:
        if not 1 <= max_depth <= 12 or not 1 <= min_leaf <= 64:
            raise ValueError("invalid tree bounds")
        self.max_depth = max_depth
        self.min_leaf = min_leaf
        self.root: TreeNode | None = None
        self.feature_count = 0

    @staticmethod
    def _prediction(rows: tuple[FeatureRow, ...]) -> bool:
        positives = sum(row.failed for row in rows)
        return positives > len(rows) - positives

    @staticmethod
    def _weighted_impurity(groups: tuple[tuple[FeatureRow, ...], tuple[FeatureRow, ...]]) -> Fraction:
        total = sum(len(group) for group in groups)
        impurity = Fraction(0)
        for group in groups:
            positives = sum(row.failed for row in group)
            negatives = len(group) - positives
            if positives and negatives:
                impurity += Fraction(len(group), total) * Fraction(2 * positives * negatives, len(group) ** 2)
        return impurity

    def _build(
        self,
        rows: tuple[FeatureRow, ...],
        features: frozenset[str],
        depth: int,
    ) -> TreeNode:
        prediction = self._prediction(rows)
        if depth >= self.max_depth or len({row.failed for row in rows}) == 1 or not features:
            return TreeNode(prediction)
        candidates: list[
            tuple[Fraction, str, tuple[FeatureRow, ...], tuple[FeatureRow, ...]]
        ] = []
        for feature in features:
            absent = tuple(row for row in rows if row.features.get(feature, 0) <= 0)
            present = tuple(row for row in rows if row.features.get(feature, 0) > 0)
            if len(absent) < self.min_leaf or len(present) < self.min_leaf:
                continue
            candidates.append((self._weighted_impurity((absent, present)), feature, absent, present))
        if not candidates:
            return TreeNode(prediction)
        _, feature, absent, present = min(candidates, key=lambda item: (item[0], item[1]))
        remaining = features - {feature}
        return TreeNode(
            prediction,
            feature,
            self._build(absent, remaining, depth + 1),
            self._build(present, remaining, depth + 1),
        )

    def fit(self, rows: Iterable[FeatureRow]) -> "RelationalDecisionTree":
        materialized = tuple(rows)
        if not materialized or {row.failed for row in materialized} != {False, True}:
            raise ValueError("tree training requires both outcome classes")
        counts: dict[str, int] = {}
        for row in materialized:
            for feature, value in row.features.items():
                if value > 0:
                    counts[feature] = counts.get(feature, 0) + 1
        features = frozenset(
            feature
            for feature, count in counts.items()
            if self.min_leaf <= count <= len(materialized) - self.min_leaf
        )
        self.feature_count = len(features)
        self.root = self._build(materialized, features, 0)
        return self

    def predict(self, features: dict[str, int]) -> bool:
        if self.root is None:
            raise RuntimeError("tree is not fitted")
        node = self.root
        while node.feature is not None:
            next_node = node.present if features.get(node.feature, 0) > 0 else node.absent
            if next_node is None:  # pragma: no cover - constructor invariant
                raise RuntimeError("invalid tree node")
            node = next_node
        return node.prediction

    def depth(self) -> int:
        def visit(node: TreeNode | None) -> int:
            if node is None or node.feature is None:
                return 0
            return 1 + max(visit(node.absent), visit(node.present))

        if self.root is None:
            raise RuntimeError("tree is not fitted")
        return visit(self.root)


class MarginPerceptron:
    """Integer sparse margin perceptron; no floating optimizer or hidden seed."""

    def __init__(self, *, epochs: int, margin: int = 1) -> None:
        if not 1 <= epochs <= 128 or not 0 <= margin <= 16:
            raise ValueError("invalid perceptron bounds")
        self.epochs = epochs
        self.margin = margin
        self.weights: dict[str, int] = {}
        self.bias = 0

    def fit(self, rows: Iterable[FeatureRow]) -> "MarginPerceptron":
        materialized = tuple(rows)
        if not materialized or {row.failed for row in materialized} != {False, True}:
            raise ValueError("perceptron training requires both outcome classes")
        self.weights = {}
        self.bias = 0
        for epoch in range(self.epochs):
            ordered = materialized if epoch % 2 == 0 else tuple(reversed(materialized))
            for row in ordered:
                label = 1 if row.failed else -1
                score = self.bias + sum(
                    self.weights.get(feature, 0) * value
                    for feature, value in row.features.items()
                )
                if label * score <= self.margin:
                    for feature, value in row.features.items():
                        updated = self.weights.get(feature, 0) + label * value
                        if updated:
                            self.weights[feature] = updated
                        else:
                            self.weights.pop(feature, None)
                    self.bias += label
        return self

    def predict(self, features: dict[str, int]) -> bool:
        score = self.bias + sum(
            self.weights.get(feature, 0) * value for feature, value in features.items()
        )
        return score > 0

    @property
    def feature_count(self) -> int:
        return len(self.weights)


class HighPrecisionRelationalRuleSet:
    """Minimum-description DNF over generic one- and two-feature relations.

    Candidate rules must have zero observed negative support and a declared
    minimum positive support.  For every positive training example, the model
    retains every equally simple minimum-cost explanation.  Keeping the tied
    explanations prevents an arbitrary lexical tie-break from becoming a
    brittle shortcut under a nuisance interaction.
    """

    def __init__(self, *, min_support: int) -> None:
        if not 2 <= min_support <= 256:
            raise ValueError("invalid rule-set support bound")
        self.min_support = min_support
        self.rules: tuple[tuple[str, ...], ...] = ()
        self.positive_examples = 0
        self.covered_positive_examples = 0

    def fit(self, rows: Iterable[FeatureRow]) -> "HighPrecisionRelationalRuleSet":
        materialized = tuple(rows)
        positives = [frozenset(row.features) for row in materialized if row.failed]
        negatives = [frozenset(row.features) for row in materialized if not row.failed]
        if not positives or not negatives:
            raise ValueError("rule-set training requires both outcome classes")
        positive_support: Counter[str] = Counter()
        negative_support: Counter[str] = Counter()
        for features in positives:
            positive_support.update(features)
        for features in negatives:
            negative_support.update(features)
        frequent = frozenset(
            feature for feature, count in positive_support.items() if count >= self.min_support
        )
        coverage: dict[tuple[str, ...], set[int]] = defaultdict(set)
        for index, features in enumerate(positives):
            present = sorted(features & frequent)
            for feature in present:
                if negative_support[feature] == 0:
                    coverage[(feature,)].add(index)
            for pair in combinations(present, 2):
                coverage[pair].add(index)
        negative_pairs: set[tuple[str, str]] = set()
        for features in negatives:
            present = sorted(features & frequent)
            negative_pairs.update(combinations(present, 2))
        candidates = {
            rule: covered
            for rule, covered in coverage.items()
            if len(covered) >= self.min_support
            and (len(rule) == 1 or rule not in negative_pairs)
        }
        def feature_cost(feature: str) -> int:
            if feature.startswith(("event:", "scalar:")):
                return 1
            if feature.startswith(("bigram:", "relation:", "same-task:")):
                return 2
            return 3

        by_positive: dict[int, list[tuple[str, ...]]] = defaultdict(list)
        for rule, covered in candidates.items():
            for index in covered:
                by_positive[index].append(rule)
        selected: set[tuple[str, ...]] = set()
        uncovered: set[int] = set()
        for index in range(len(positives)):
            options = by_positive[index]
            if not options:
                uncovered.add(index)
                continue
            minimum = min(sum(feature_cost(feature) for feature in rule) for rule in options)
            selected.update(
                rule
                for rule in options
                if sum(feature_cost(feature) for feature in rule) == minimum
            )
        self.rules = tuple(sorted(selected, key=lambda rule: (len(rule), rule)))
        self.positive_examples = len(positives)
        self.covered_positive_examples = len(positives) - len(uncovered)
        return self

    def predict(self, features: dict[str, int]) -> bool:
        present = features.keys()
        return any(all(feature in present for feature in rule) for rule in self.rules)

    @property
    def feature_count(self) -> int:
        return len({feature for rule in self.rules for feature in rule})
