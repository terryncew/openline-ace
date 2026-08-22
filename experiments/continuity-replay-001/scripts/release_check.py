from __future__ import annotations
import ast
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd):
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(ROOT) if not existing else str(ROOT) + os.pathsep + existing
    )
    subprocess.run(cmd, cwd=ROOT, check=True, env=env)


def main():
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([sys.executable, "scripts/verify_no_leakage.py"])
    run([sys.executable, "scripts/evaluate_heldout.py"])
    run([sys.executable, "scripts/verify_evidence.py"])
    py = list(ROOT.rglob("*.py"))
    for version in ((3, 11), (3, 12), (3, 13)):
        for path in py:
            ast.parse(
                path.read_text(encoding="utf-8"),
                filename=str(path),
                feature_version=version,
            )
    print(
        "continuity_replay_release_check_pass "
        "python_files=" + str(len(py))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
