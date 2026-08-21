from __future__ import annotations

import unittest
from pathlib import Path

from rcdl.canonical import (
    CanonicalizationError,
    canonical_digest,
    canonical_json,
    load_json_bytes,
)
from rcdl.model import Clause, ClauseValidationError
from rcdl.raft import raft_candidate_clauses

ROOT = Path(__file__).resolve().parents[1]


class CanonicalTests(unittest.TestCase):
    def test_object_order_does_not_change_bytes(self) -> None:
        left = {"b": 2, "a": [True, "x"]}
        right = {"a": [True, "x"], "b": 2}
        self.assertEqual(canonical_json(left), canonical_json(right))
        self.assertEqual(canonical_digest(left), canonical_digest(right))

    def test_float_is_rejected(self) -> None:
        with self.assertRaises(CanonicalizationError):
            canonical_json({"score": 0.5})

    def test_duplicate_json_key_is_rejected(self) -> None:
        with self.assertRaises(CanonicalizationError):
            load_json_bytes(b'{"a":1,"a":2}')

    def test_non_nfc_string_is_rejected(self) -> None:
        with self.assertRaises(CanonicalizationError):
            canonical_json({"value": "e\u0301"})

    def test_out_of_range_integer_is_rejected(self) -> None:
        with self.assertRaises(CanonicalizationError):
            canonical_json({"value": 2**63})


class ClauseTests(unittest.TestCase):
    def test_frozen_candidates_are_unique_and_valid(self) -> None:
        clauses = raft_candidate_clauses()
        self.assertEqual(len(clauses), 7)
        self.assertEqual(len({item.id for item in clauses}), 7)
        self.assertEqual(len({item.digest for item in clauses}), 7)

    def test_example_files_match_frozen_candidates(self) -> None:
        expected = {clause.id: clause.digest for clause in raft_candidate_clauses()}
        observed = {}
        for path in sorted((ROOT / "clauses").glob("*.json")):
            clause = Clause.from_path(path)
            observed[clause.id] = clause.digest
        self.assertEqual(observed, expected)

    def test_unknown_top_level_field_is_rejected(self) -> None:
        document = raft_candidate_clauses()[0].to_dict()
        document["oracle_result"] = True
        with self.assertRaises(ClauseValidationError):
            Clause.from_dict(document)

    def test_oracle_and_intervention_labels_are_unavailable_to_clauses(self) -> None:
        for forbidden in ("oracle_passed", "failed_properties", "arm", "hook"):
            document = raft_candidate_clauses()[0].to_dict()
            document["trigger"]["where"] = {forbidden: True}
            with self.subTest(field=forbidden), self.assertRaises(ClauseValidationError):
                Clause.from_dict(document)

    def test_five_way_join_is_rejected(self) -> None:
        document = raft_candidate_clauses()[1].to_dict()
        document["require"]["joins"]["index"] = "index"
        document["require"]["joins"]["digest"] = "digest"
        with self.assertRaises(ClauseValidationError):
            Clause.from_dict(document)

    def test_bad_majority_field_is_rejected(self) -> None:
        document = raft_candidate_clauses()[4].to_dict()
        document["require"]["threshold"]["field"] = "Bad Field"
        with self.assertRaises(ClauseValidationError):
            Clause.from_dict(document)

    def test_document_copy_does_not_mutate_clause(self) -> None:
        clause = raft_candidate_clauses()[0]
        document = clause.to_dict()
        document["id"] = "changed"
        self.assertEqual(clause.id, "raft.vote_once_per_term")


if __name__ == "__main__":
    unittest.main()
