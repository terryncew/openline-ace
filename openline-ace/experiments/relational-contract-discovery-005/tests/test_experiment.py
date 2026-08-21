from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from rcdl005.canonical import canonical_json, load_json_bytes
from rcdl005.experiment import run_experiment
from rcdl005.verification import verify_manifest, verify_projection


class ExperimentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.summary = run_experiment(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_summary_boundary(self) -> None:
        self.assertEqual(self.summary["scientific_verdict"], "CAUSAL_UTILITY_PARITY")
        self.assertFalse(self.summary["promotion_authorized"])

    def test_manifest_verifies(self) -> None:
        self.assertTrue(verify_manifest(self.root / "causal-utility-manifest.json").to_dict()["verified"])

    def test_projection_verifies(self) -> None:
        self.assertTrue(verify_projection(self.root / "verified-handoff-projection.json").to_dict()["verified"])

    def test_nonempty_output_refuses_overwrite(self) -> None:
        with self.assertRaises(FileExistsError):
            run_experiment(self.root)

    def test_force_replay_is_byte_deterministic(self) -> None:
        before = {path.name: path.read_bytes() for path in self.root.iterdir()}
        run_experiment(self.root, force=True)
        after = {path.name: path.read_bytes() for path in self.root.iterdir()}
        self.assertEqual(before, after)

    def test_manifest_tamper_is_rejected(self) -> None:
        path = self.root / "causal-utility-manifest.json"
        document = load_json_bytes(path.read_bytes())
        document = copy.deepcopy(document)
        document["ace"]["promotion_authorized"] = True
        path.write_bytes(canonical_json(document) + b"\n")
        with self.assertRaises(ValueError):
            verify_manifest(path)


if __name__ == "__main__":
    unittest.main()

