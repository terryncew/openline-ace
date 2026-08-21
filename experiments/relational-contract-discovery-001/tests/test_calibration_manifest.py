from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from rcdl.calibration import run_calibration
from rcdl.canonical import canonical_json
from rcdl.manifest import ManifestVerificationError, verify_manifest
from rcdl.projection import ProjectionVerificationError, verify_projection
from rcdl.raft import SAFETY_CLAUSE_IDS, SPURIOUS_CONTROL_IDS


class CalibrationTests(unittest.TestCase):
    def test_full_calibration_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            summary = run_calibration(directory, trials=2)
            self.assertEqual(summary["verdict"], "CALIBRATION_PASS")
            self.assertEqual(summary["supported_clause_count"], 6)
            self.assertEqual(summary["rejected_clause_count"], 1)
            self.assertEqual(summary["spurious_control_rejected_count"], 1)
            self.assertEqual(summary["minimal_family_count"], 1)
            verification = verify_manifest(Path(directory) / "contract-manifest.json")
            self.assertEqual(verification.verdict, "CALIBRATION_PASS")
            projection = verify_projection(Path(directory) / "contract-projection.json")
            self.assertEqual(projection.authorization, "NONE")
            self.assertEqual(projection.claim_count, 6)

    def test_calibration_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            run_calibration(left, trials=2)
            run_calibration(right, trials=2)
            self.assertEqual(
                (Path(left) / "contract-manifest.json").read_bytes(),
                (Path(right) / "contract-manifest.json").read_bytes(),
            )
            self.assertEqual(
                (Path(left) / "summary.json").read_bytes(),
                (Path(right) / "summary.json").read_bytes(),
            )

    def test_minimal_family_contains_all_necessary_clauses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_calibration(directory, trials=2)
            document = json.loads((Path(directory) / "contract-manifest.json").read_text())
            expected = sorted(SAFETY_CLAUSE_IDS)
            self.assertEqual(document["minimal_contract_families"], [expected])
            self.assertEqual(document["ace"]["level"], "1_CANDIDATE")
            self.assertFalse(document["ace"]["promotion_authorized"])
            self.assertEqual(document["model_reference"]["tlc_execution"], "NOT_RUN")

    def test_observational_spurious_control_is_mined_then_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_calibration(directory, trials=2)
            document = json.loads((Path(directory) / "contract-manifest.json").read_text())
            mined = {
                item["clause_id"]: item
                for item in document["candidate_mining"]["results"]
            }
            records = {item["id"]: item for item in document["clauses"]}
            for clause_id in SPURIOUS_CONTROL_IDS:
                self.assertTrue(mined[clause_id]["accepted"])
                self.assertEqual(records[clause_id]["standing"], "REJECTED")
                self.assertEqual(
                    records[clause_id]["standing_reason"],
                    "REJECTED_CAUSALLY_IRRELEVANT",
                )

    def test_representative_active_and_sham_traces_are_written(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_calibration(directory, trials=2)
            traces = list((Path(directory) / "representative-traces").glob("*.json"))
            self.assertEqual(len(traces), 14)

    def test_nonempty_output_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "user-file.txt").write_text("preserve me", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                run_calibration(directory, trials=2)
            self.assertEqual((Path(directory) / "user-file.txt").read_text(), "preserve me")

    def test_manifest_tamper_breaks_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_calibration(directory, trials=2)
            path = Path(directory) / "contract-manifest.json"
            document = json.loads(path.read_text())
            document["tool_version"] = "tampered"
            path.write_bytes(canonical_json(document) + b"\n")
            with self.assertRaises(ManifestVerificationError):
                verify_manifest(path)

    def test_rehashed_manifest_cannot_promote_spurious_control(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_calibration(directory, trials=2)
            path = Path(directory) / "contract-manifest.json"
            document = json.loads(path.read_text())
            control = next(
                item
                for item in document["clauses"]
                if item["id"] in SPURIOUS_CONTROL_IDS
            )
            control["standing"] = "SUPPORTED"
            control["standing_reason"] = "INTERVENTIONALLY_NECESSARY"
            payload = canonical_json(document) + b"\n"
            path.write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            path.with_suffix(".json.sha256").write_text(
                f"{digest}  {path.name}\n", encoding="utf-8"
            )
            with self.assertRaises(ManifestVerificationError):
                verify_manifest(path)

    def test_missing_sidecar_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_calibration(directory, trials=2)
            path = Path(directory) / "contract-manifest.json"
            path.with_suffix(".json.sha256").unlink()
            with self.assertRaises(ManifestVerificationError):
                verify_manifest(path)

    def test_projection_cannot_self_authorize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_calibration(directory, trials=2)
            path = Path(directory) / "contract-projection.json"
            document = json.loads(path.read_text())
            document["authority"]["authorization"] = "COMMIT"
            path.write_bytes(canonical_json(document) + b"\n")
            with self.assertRaises(ProjectionVerificationError):
                verify_projection(path)


if __name__ == "__main__":
    unittest.main()
