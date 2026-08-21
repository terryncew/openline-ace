from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from rcdl002.engine_reference import (
    REFERENCE_PATH,
    EngineReferenceError,
    verify_engine_reference,
)

ROOT = Path(__file__).resolve().parents[1]
ENGINE_ROOT = ROOT.parent / "relational-contract-discovery-001"


class EngineReferenceTests(unittest.TestCase):
    def test_frozen_engine_reference_matches(self) -> None:
        result = verify_engine_reference()
        self.assertFalse(result.to_dict()["engine_modified"])
        self.assertEqual(result.file_count, 9)
        self.assertEqual(len(result.aggregate_sha256), 64)

    def test_modified_frozen_engine_file_is_rejected(self) -> None:
        reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            experiments = Path(directory) / "experiments"
            copied_engine = experiments / "relational-contract-discovery-001"
            copied_reference = (
                experiments
                / "relational-contract-discovery-002"
                / "references"
                / REFERENCE_PATH.name
            )
            copied_reference.parent.mkdir(parents=True)
            shutil.copy2(REFERENCE_PATH, copied_reference)
            for item in reference["files"]:
                source = ENGINE_ROOT / item["path"]
                target = copied_engine / item["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            changed = copied_engine / reference["files"][0]["path"]
            with changed.open("ab") as handle:
                handle.write(b"\n# deliberate tamper\n")
            with self.assertRaisesRegex(EngineReferenceError, "frozen engine file changed"):
                verify_engine_reference(copied_reference)

    def test_engine_reference_rejects_path_escape(self) -> None:
        reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
        reference["files"][0]["path"] = "../escape.py"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "experiments" / "relational-contract-discovery-002"
            path = target / "references" / "reference.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(reference), encoding="utf-8")
            with self.assertRaises(EngineReferenceError):
                verify_engine_reference(path)


if __name__ == "__main__":
    unittest.main()
