import unittest

from aca001.model import validate_candidate
from aca001.conformance import fixture_candidates


class CandidateBoundaryTests(unittest.TestCase):
    def test_fixture_candidates_validate(self):
        for candidate in fixture_candidates():
            self.assertEqual(validate_candidate(candidate)["source"]["authority"], "NONE")

    def test_proposer_cannot_self_certify(self):
        candidate = fixture_candidates()[0]
        mutated = {**candidate, "verdict": "SUPPORTED"}
        with self.assertRaises(ValueError):
            validate_candidate(mutated)

    def test_artifact_valid_is_forbidden(self):
        candidate = fixture_candidates()[0]
        mutated = dict(candidate)
        mutated["relation"] = {**candidate["relation"], "artifact_valid": True}
        with self.assertRaises(ValueError):
            validate_candidate(mutated)


if __name__ == "__main__":
    unittest.main()
