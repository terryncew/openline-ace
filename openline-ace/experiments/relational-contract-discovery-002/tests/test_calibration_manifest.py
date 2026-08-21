from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rcdl.canonical import load_json_bytes

from rcdl002.calibration import run_calibration
from rcdl002.manifest import (
    ManifestVerificationError,
    verify_manifest,
    write_manifest,
)
from rcdl002.projection import (
    ProjectionVerificationError,
    verify_projection,
    write_projection,
)
from rcdl002.workflow import TARGET_CLAUSE_IDS


class CalibrationManifestTests(unittest.TestCase):
    def test_closed_loop_calibration_recovers_only_the_target_family(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "calibration"
            summary = run_calibration(output, trials=2)
            self.assertEqual(summary["verdict"], "CALIBRATION_PASS")
            self.assertEqual(summary["candidate_clause_count"], 5)
            self.assertEqual(summary["supported_clause_count"], 4)
            self.assertEqual(summary["rejected_clause_count"], 1)
            self.assertEqual(summary["spurious_control_rejected_count"], 1)
            self.assertEqual(summary["minimal_family_count"], 1)
            self.assertEqual(summary["bounded_recovery_supported_count"], 1)
            self.assertFalse(summary["engine_modified"])
            manifest = load_json_bytes((output / "contract-manifest.json").read_bytes())
            self.assertEqual(
                manifest["minimal_contract_families"],
                [sorted(TARGET_CLAUSE_IDS)],
            )
            self.assertEqual(
                len(list((output / "representative-traces").glob("*.json"))),
                10,
            )
            self.assertEqual(verify_manifest(output / "contract-manifest.json").verdict, "CALIBRATION_PASS")
            self.assertEqual(verify_projection(output / "contract-projection.json").authorization, "NONE")

    def test_replay_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            run_calibration(first, trials=2)
            run_calibration(second, trials=2)
            for filename in (
                "contract-manifest.json",
                "contract-manifest.json.sha256",
                "contract-projection.json",
                "contract-projection.json.sha256",
                "summary.json",
            ):
                with self.subTest(filename=filename):
                    self.assertEqual(
                        (first / filename).read_bytes(),
                        (second / filename).read_bytes(),
                    )

    def test_nonempty_output_requires_explicit_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            marker = output / "preserve-me"
            marker.write_text("user data", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                run_calibration(output, trials=2)
            self.assertEqual(marker.read_text(encoding="utf-8"), "user data")

    def test_manifest_digest_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "calibration"
            run_calibration(output, trials=2)
            manifest = output / "contract-manifest.json"
            manifest.write_bytes(manifest.read_bytes() + b" ")
            with self.assertRaises(ManifestVerificationError):
                verify_manifest(manifest)

    def test_rehashed_manifest_cannot_promote_itself(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "calibration"
            run_calibration(output, trials=2)
            path = output / "contract-manifest.json"
            document = load_json_bytes(path.read_bytes())
            document["ace"]["level"] = "4_FORMAL_RESULT"
            document["ace"]["promotion_authorized"] = True
            write_manifest(document, path)
            with self.assertRaisesRegex(ManifestVerificationError, "unauthorized promotion"):
                verify_manifest(path)

    def test_rehashed_spurious_control_promotion_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "calibration"
            run_calibration(output, trials=2)
            path = output / "contract-manifest.json"
            document = load_json_bytes(path.read_bytes())
            control = next(
                item
                for item in document["clauses"]
                if item["calibration_role"] == "spurious_observational_control"
            )
            control["standing"] = "SUPPORTED"
            control["standing_reason"] = "INTERVENTIONALLY_NECESSARY"
            write_manifest(document, path)
            with self.assertRaisesRegex(ManifestVerificationError, "spurious control"):
                verify_manifest(path)

    def test_rehashed_clause_digest_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "calibration"
            run_calibration(output, trials=2)
            path = output / "contract-manifest.json"
            document = load_json_bytes(path.read_bytes())
            document["clauses"][0]["digest"] = "0" * 64
            write_manifest(document, path)
            with self.assertRaisesRegex(ManifestVerificationError, "source binding"):
                verify_manifest(path)

    def test_rehashed_intervention_rate_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "calibration"
            run_calibration(output, trials=2)
            path = output / "contract-manifest.json"
            document = load_json_bytes(path.read_bytes())
            document["clauses"][0]["intervention"][
                "active_oracle_failure_rate_ppm"
            ] = 0
            write_manifest(document, path)
            with self.assertRaisesRegex(ManifestVerificationError, "rate mismatch"):
                verify_manifest(path)

    def test_rehashed_projection_cannot_grant_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "calibration"
            run_calibration(output, trials=2)
            path = output / "contract-projection.json"
            document = load_json_bytes(path.read_bytes())
            document["authority"]["authorization"] = "ALLOW"
            write_projection(document, path)
            with self.assertRaisesRegex(ProjectionVerificationError, "authority boundary"):
                verify_projection(path)

    def test_trial_bounds_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for trials in (1, 65, True, 2.5):
                with self.subTest(trials=trials):
                    with self.assertRaises(ValueError):
                        run_calibration(Path(directory) / str(trials), trials=trials)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
