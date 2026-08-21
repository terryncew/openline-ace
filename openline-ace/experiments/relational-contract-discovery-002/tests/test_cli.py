from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from rcdl002.cli import main


class CliTests(unittest.TestCase):
    def test_verify_engine(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["verify-engine"])
        result = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(result["verified"])
        self.assertFalse(result["engine_modified"])

    def test_show_candidates_has_no_standing(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["show-candidates"])
        result = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(len(result["clauses"]), 5)
        self.assertTrue(all("standing" not in item for item in result["clauses"]))

    def test_calibrate_then_verify_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "out"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(
                    ["calibrate", "--output", str(output_path), "--trials", "2"]
                )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue())["verdict"], "CALIBRATION_PASS")
            for command, filename in (
                ("verify-manifest", "contract-manifest.json"),
                ("verify-projection", "contract-projection.json"),
            ):
                with self.subTest(command=command):
                    captured = io.StringIO()
                    with contextlib.redirect_stdout(captured):
                        verify_code = main([command, str(output_path / filename)])
                    self.assertEqual(verify_code, 0)
                    self.assertTrue(json.loads(captured.getvalue())["verified"])

    def test_missing_manifest_returns_machine_readable_error(self) -> None:
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            code = main(["verify-manifest", "/definitely/missing.json"])
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(error.getvalue())["ok"])


if __name__ == "__main__":
    unittest.main()
