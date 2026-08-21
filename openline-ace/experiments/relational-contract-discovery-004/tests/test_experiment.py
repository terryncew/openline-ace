from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcdl.canonical import load_json_bytes

from rcdl004.experiment import run_experiment
from rcdl004.manifest import ManifestVerificationError, verify_manifest, write_bound_json
from rcdl004.projection import (
    ProjectionVerificationError,
    verify_projection,
    write_projection,
)


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temporary.name) / "pressure-test"
        cls.summary = run_experiment(cls.output)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_outputs_verify(self) -> None:
        verified = verify_manifest(self.output / "pressure-test-manifest.json")
        self.assertEqual(verified.scientific_verdict, "LEARNED_PARITY")
        projection = verify_projection(self.output / "contract-projection.json")
        self.assertEqual(projection.predictive_standing, "REJECTED_BY_BOUNDED_LEARNED_PARITY")

    def test_summary_keeps_software_and_scientific_verdicts_separate(self) -> None:
        self.assertEqual(self.summary["verdict"], "PRESSURE_TEST_VALID_LEARNED_PARITY")
        self.assertEqual(
            self.summary["claim_effect"],
            "PREDICTIVE_SUPERIORITY_FALSIFIED_WITHIN_TOURNAMENT",
        )

    def test_manifest_rejects_authority_expansion_even_when_rehashed(self) -> None:
        source = self.output / "pressure-test-manifest.json"
        document = load_json_bytes(source.read_bytes())
        document["ace"]["promotion_authorized"] = True
        target = self.output / "tampered-authority.json"
        write_bound_json(document, target)
        with self.assertRaises(ManifestVerificationError):
            verify_manifest(target)

    def test_manifest_rejects_fabricated_score_even_when_rehashed(self) -> None:
        source = self.output / "pressure-test-manifest.json"
        document = load_json_bytes(source.read_bytes())
        document["tournament"]["best_learned_score"]["false_positive"] = 1
        target = self.output / "tampered-score.json"
        write_bound_json(document, target)
        with self.assertRaises(ManifestVerificationError):
            verify_manifest(target)

    def test_manifest_rejects_prediction_mutation(self) -> None:
        prediction = self.output / "predictions.jsonl"
        original = prediction.read_bytes()
        prediction.write_bytes(original + b"\n")
        try:
            with self.assertRaises(ManifestVerificationError):
                verify_manifest(self.output / "pressure-test-manifest.json")
        finally:
            prediction.write_bytes(original)

    def test_projection_rejects_policy_authority_even_when_rehashed(self) -> None:
        source = self.output / "contract-projection.json"
        document = load_json_bytes(source.read_bytes())
        document["receipt_gate"]["eligible_as_policy_input"] = True
        target = self.output / "tampered-projection.json"
        write_projection(document, target)
        with self.assertRaises(ProjectionVerificationError):
            verify_projection(target)

    def test_non_empty_output_requires_force(self) -> None:
        with self.assertRaises(FileExistsError):
            run_experiment(self.output)


if __name__ == "__main__":
    unittest.main()

