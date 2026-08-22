from __future__ import annotations

import unittest

from ccr.baselines import flat_registry, global_invalidation
from ccr.engine import selective_reverification
from ccr.metrics import score
from ccr.model import ClaimGraph


class CCR001Tests(unittest.TestCase):
    def setUp(self):
        self.graph = ClaimGraph(
            claims=frozenset({"direct", "descendant", "independent"}),
            edges=(
                ("artifact:changed", "direct"),
                ("direct", "descendant"),
                ("artifact:other", "independent"),
            ),
        )
        self.changed = frozenset({"artifact:changed"})
        self.oracle = frozenset({"direct", "descendant"})

    def test_selective_reopens_descendants_only(self):
        prediction = selective_reverification(self.graph, self.changed)
        self.assertEqual(prediction.reopened, frozenset({"direct", "descendant"}))
        self.assertEqual(prediction.retained, frozenset({"independent"}))

    def test_flat_misses_descendant(self):
        prediction = flat_registry(self.graph, self.changed)
        metrics = score(prediction, self.oracle)
        self.assertEqual(prediction.reopened, frozenset({"direct"}))
        self.assertEqual(metrics["missed_reopenings"], 1)

    def test_global_reopens_independent_claim(self):
        prediction = global_invalidation(self.graph, self.changed)
        metrics = score(prediction, self.oracle)
        self.assertEqual(metrics["excess_reviews"], 1)

    def test_empty_change_retains_all(self):
        prediction = selective_reverification(self.graph, frozenset())
        self.assertEqual(prediction.reopened, frozenset())
        self.assertEqual(prediction.retained, self.graph.claims)

    def test_cycle_is_bounded(self):
        graph = ClaimGraph(
            claims=frozenset({"a", "b", "independent"}),
            edges=(
                ("artifact:x", "a"),
                ("a", "b"),
                ("b", "a"),
            ),
        )
        prediction = selective_reverification(graph, frozenset({"artifact:x"}))
        self.assertEqual(prediction.reopened, frozenset({"a", "b"}))


if __name__ == "__main__":
    unittest.main()
