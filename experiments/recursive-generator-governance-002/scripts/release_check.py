from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
steps = [
    [sys.executable, "scripts/verify_source.py"],
    [sys.executable, "scripts/verify_preregistration.py"],
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
    [sys.executable, "scripts/verify_freeze.py"],
]
for cmd in steps:
    subprocess.run(cmd, cwd=ROOT, check=True)
print("PASS RGG-002 release check")
