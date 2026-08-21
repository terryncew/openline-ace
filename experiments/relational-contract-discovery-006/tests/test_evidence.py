from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from rcdl006.canonical import write_canonical
from rcdl006.evidence import EXPERIMENT_ROOT, freeze_evidence, verify_evidence
from rcdl006.tournament import run_tournament


def passing_release() -> dict[str, object]:
    return {
        "compileall": "PASS",
        "deterministic_replay": "PASS",
        "fixture_boundary": "PASS",
        "isolated_copy": "PASS",
        "manifest_projection": "PASS",
        "policy_boundary": "PASS",
        "randomized_probe": {"comparisons": 5000, "mismatches": 0, "samples": 385, "seed": 6006, "status": "PASS"},
        "schema": "rcdl.release-check/0.6",
        "unit_tests": {"status": "PASS", "test_count": 40},
        "upstream_boundary": "PASS",
        "verdict": "PASS",
    }


class EvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "experiment"
        shutil.copytree(
            EXPERIMENT_ROOT,
            self.root,
            ignore=shutil.ignore_patterns("evidence", "__pycache__", "*.pyc"),
        )
        output = self.root / "evidence" / "heldout-mechanism"
        run_tournament(output)
        write_canonical(self.root / "evidence" / "release-check.json", passing_release())
        freeze_evidence(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_frozen_evidence_roundtrip(self) -> None:
        result = verify_evidence(self.root)
        self.assertTrue(result["verified"])
        self.assertEqual(result["policy_authority"], "NONE")

    def test_receipt_tamper_is_rejected(self) -> None:
        path = self.root / "evidence" / "experiment-receipt.json"
        payload = bytearray(path.read_bytes())
        payload[10] ^= 1
        path.write_bytes(bytes(payload))
        with self.assertRaises(ValueError):
            verify_evidence(self.root)

    def test_added_evidence_file_is_rejected(self) -> None:
        (self.root / "evidence" / "unindexed.txt").write_text("extra", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "closure mismatch"):
            verify_evidence(self.root)

    def test_source_change_reopens_receipt(self) -> None:
        path = self.root / "README.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "body binding"):
            verify_evidence(self.root)

    def test_release_failure_cannot_be_frozen(self) -> None:
        other = Path(self.tmp.name) / "failed"
        shutil.copytree(self.root, other)
        release = passing_release()
        release["verdict"] = "FAIL"
        write_canonical(other / "evidence" / "release-check.json", release)
        with self.assertRaisesRegex(ValueError, "did not pass"):
            freeze_evidence(other)


if __name__ == "__main__":
    unittest.main()
