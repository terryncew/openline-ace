from __future__ import annotations

import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
for script in (
    "verify_freeze.py",
    "verify_upstream_assurance.py",
    "verify_external_task.py",
    "run_controls.py",
):
    subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT, check=True)
subprocess.run(
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
    cwd=ROOT,
    check=True,
)
print("PASS FAR-006 release check")
