from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command):
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([sys.executable, "-m", "drift_observer"])
    run([sys.executable, "scripts/verify_evidence.py"])

    files = list(ROOT.rglob("*.py"))
    for version in ((3, 11), (3, 12), (3, 13)):
        for path in files:
            ast.parse(
                path.read_text(encoding="utf-8"),
                filename=str(path),
                feature_version=version,
            )
    print(f"drift_observer_release_check_pass python_files={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
