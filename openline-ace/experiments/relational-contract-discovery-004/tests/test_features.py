from __future__ import annotations

import unittest

from rcdl.nuisance import nuisance_variants

from rcdl004.corpus import load_frozen_corpus
from rcdl004.features import (
    combined_features,
    feature_schema_digest,
    graph_features,
    sequence_features,
    task_segments,
)


class FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        corpus = load_frozen_corpus()
        cls.single = corpus.split("train")[0].trace
        cls.multi = corpus.split("test")[-1].trace

    def test_actor_renaming_is_invariant(self) -> None:
        renamed = nuisance_variants(self.single)[0]
        self.assertEqual(sequence_features(self.single), sequence_features(renamed))
        self.assertEqual(graph_features(self.single), graph_features(renamed))

    def test_event_id_renumbering_is_invariant(self) -> None:
        renumbered = nuisance_variants(self.single)[1]
        self.assertEqual(combined_features(self.single), combined_features(renumbered))

    def test_raw_identity_values_never_appear_in_feature_names(self) -> None:
        names = "\n".join(combined_features(self.single))
        self.assertNotIn(self.single.run_id, names)
        for event in self.single.events:
            for key in ("task_id", "patch_hash"):
                value = event.attrs.get(key)
                if isinstance(value, str):
                    self.assertNotIn(value, names)

    def test_task_bag_uses_identity_equality_without_exposing_values(self) -> None:
        segments = task_segments(self.multi)
        self.assertGreaterEqual(len(segments), 2)
        self.assertEqual(sum(len(segment.events) for segment in segments), len(self.multi.events))

    def test_feature_schema_digest_is_stable_shape(self) -> None:
        digest = feature_schema_digest()
        self.assertEqual(len(digest), 64)
        int(digest, 16)


if __name__ == "__main__":
    unittest.main()

