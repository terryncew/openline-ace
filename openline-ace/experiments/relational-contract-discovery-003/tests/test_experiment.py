from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcdl.canonical import load_json_bytes

from rcdl003.experiment import run_experiment
from rcdl003.manifest import (
    ManifestVerificationError,
    verify_manifest,
    write_bound_json,
)
from rcdl003.projection import (
    ProjectionVerificationError,
    verify_projection,
    write_projection,
)


class ExperimentTests(unittest.TestCase):
    def _run(self, root: Path) -> Path:
        output = root / "replication"
        summary = run_experiment(output, trials=2)
        self.assertEqual(summary["verdict"], "REPLICATION_PASS_RCDL_STRICT_WIN")
        return output

    def test_experiment_outputs_verify(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = self._run(Path(temporary))
            self.assertEqual(
                verify_manifest(output / "contract-manifest.json").verdict,
                "REPLICATION_PASS_RCDL_STRICT_WIN",
            )
            self.assertEqual(
                verify_projection(output / "contract-projection.json").claim_count, 4
            )

    def test_replay_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            left = self._run(root / "left")
            right = self._run(root / "right")
            for name in ("contract-manifest.json", "contract-projection.json", "summary.json"):
                self.assertEqual((left / name).read_bytes(), (right / name).read_bytes())

    def test_manifest_rejects_authority_expansion_even_when_rehashed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = self._run(Path(temporary))
            source = output / "contract-manifest.json"
            document = load_json_bytes(source.read_bytes())
            document["ace"]["promotion_authorized"] = True
            target = output / "tampered-manifest.json"
            write_bound_json(document, target)
            with self.assertRaises(ManifestVerificationError):
                verify_manifest(target)

    def test_manifest_rejects_fabricated_baseline_score(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = self._run(Path(temporary))
            document = load_json_bytes((output / "contract-manifest.json").read_bytes())
            score = document["baseline_tournament"]["best_ordinary_score"]
            score["accuracy_ppm"] = 1_000_000
            target = output / "fabricated-score.json"
            write_bound_json(document, target)
            with self.assertRaises(ManifestVerificationError):
                verify_manifest(target)

    def test_projection_rejects_policy_authority_even_when_rehashed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = self._run(Path(temporary))
            document = load_json_bytes((output / "contract-projection.json").read_bytes())
            document["receipt_gate"]["eligible_as_policy_input"] = True
            target = output / "tampered-projection.json"
            write_projection(document, target)
            with self.assertRaises(ProjectionVerificationError):
                verify_projection(target)

    def test_non_empty_output_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = self._run(Path(temporary))
            with self.assertRaises(FileExistsError):
                run_experiment(output, trials=2)

    def test_invalid_trial_bounds_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                run_experiment(Path(temporary) / "out", trials=1)


if __name__ == "__main__":
    unittest.main()
