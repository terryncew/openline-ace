from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "rcdl003", *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_verify_bindings(self) -> None:
        completed = self.run_cli("verify-bindings")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["verified"])

    def test_show_clauses(self) -> None:
        completed = self.run_cli("show-clauses")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(len(json.loads(completed.stdout)["clauses"]), 5)

    def test_run_and_verify(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "run"
            completed = self.run_cli(
                "run", "--output", str(output), "--trials", "2"
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                json.loads(completed.stdout)["verdict"],
                "REPLICATION_PASS_RCDL_STRICT_WIN",
            )
            verified = self.run_cli(
                "verify-manifest", str(output / "contract-manifest.json")
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)

    def test_invalid_trials_return_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            completed = self.run_cli(
                "run", "--output", temporary, "--trials", "1"
            )
            self.assertEqual(completed.returncode, 2)
            self.assertFalse(json.loads(completed.stderr)["ok"])


if __name__ == "__main__":
    unittest.main()
