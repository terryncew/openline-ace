from __future__ import annotations

import gzip
import unittest

from rcdl.canonical import canonical_json, load_json_bytes

from rcdl004.corpus import (
    EXPECTED_SPLITS,
    CorpusVerificationError,
    _parse_payload,
    load_frozen_corpus,
)


class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = load_frozen_corpus()

    def test_frozen_counts(self) -> None:
        self.assertEqual(
            {name: len(self.corpus.split(name)) for name in EXPECTED_SPLITS},
            EXPECTED_SPLITS,
        )

    def test_every_split_has_both_outcomes(self) -> None:
        for name in EXPECTED_SPLITS:
            self.assertEqual({row.failed for row in self.corpus.split(name)}, {False, True})

    def test_example_ids_are_unique(self) -> None:
        ids = [row.example_id for row in self.corpus.examples]
        self.assertEqual(len(ids), len(set(ids)))

    def test_direct_label_in_trace_is_rejected(self) -> None:
        row = self.corpus.examples[0]
        document = {
            "schema": "rcdl.learning-example/0.1",
            "example_id": row.example_id,
            "split": row.split,
            "failed": row.failed,
            "trace": row.trace.to_dict(),
        }
        document["trace"]["metadata"]["arm"] = "active"
        payload = canonical_json(document) + b"\n"
        with self.assertRaises(CorpusVerificationError):
            _parse_payload(payload)

    def test_unknown_split_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            self.corpus.split("future")


if __name__ == "__main__":
    unittest.main()

