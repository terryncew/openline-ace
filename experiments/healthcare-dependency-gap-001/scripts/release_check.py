from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd):
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not existing else str(ROOT) + os.pathsep + existing
    subprocess.run(cmd, cwd=ROOT, check=True, env=env)


def verify_manifest():
    manifest = json.loads((ROOT / "RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
    expected = set(manifest["files"])
    actual = {
        str(path.relative_to(ROOT)).replace(os.sep, "/")
        for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    if actual != expected:
        raise SystemExit(f"manifest mismatch missing={sorted(expected-actual)} excess={sorted(actual-expected)}")


def main():
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([sys.executable, "scripts/verify_evidence.py"])
    run([sys.executable, "scripts/run_audit.py"])
    verify_manifest()
    py = list(ROOT.rglob("*.py"))
    for version in ((3, 10), (3, 11), (3, 12), (3, 13)):
        for path in py:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=version)
    result = json.loads((ROOT / "evidence" / "result.json").read_text(encoding="utf-8"))
    assert result["disposition"] == "REAL_DATA_DEPENDENCY_COVERAGE_INSUFFICIENT"
    print("healthcare_dependency_gap_release_check_pass python_files=" + str(len(py)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
