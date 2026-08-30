from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT, check=True)
subprocess.run([sys.executable, "scripts/run_demo.py"], cwd=ROOT, check=True)
print("PASS fiduciary-agent-runtime-001")
