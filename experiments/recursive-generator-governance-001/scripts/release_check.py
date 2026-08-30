from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def main() -> None:
    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        check=True,
    )
    run("scripts/verify_preregistration.py")
    run("scripts/run_positive_control.py")
    run("scripts/verify_freeze.py")


if __name__ == "__main__":
    main()
