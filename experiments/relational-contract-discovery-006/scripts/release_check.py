#!/usr/bin/env python3
"""Run an isolated, deterministic release check for RCDL-006."""

from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import envharness

from rcdl006.canonical import write_canonical


ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def release_check(samples: int = 384) -> dict[str, object]:
    upstream_package = Path(inspect.getsourcefile(envharness) or "").resolve().parent
    if not upstream_package.is_dir():
        raise RuntimeError("EnvHarness source root unavailable")
    upstream_root = upstream_package.parent
    with tempfile.TemporaryDirectory() as tmp:
        isolated = Path(tmp) / "relational-contract-discovery-006"
        shutil.copytree(ROOT, isolated, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "evidence"))
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join((str(upstream_root), str(isolated)))
        compile_result = _run([sys.executable, "-m", "compileall", "-q", "."], isolated, env)
        tests = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], isolated, env)
        match = re.search(r"Ran (\d+) tests?", tests.stderr + tests.stdout)
        test_count = int(match.group(1)) if match else 0
        fixtures = _run([sys.executable, "-m", "rcdl006", "verify-fixtures"], isolated, env)
        upstream = _run([sys.executable, "-m", "rcdl006", "verify-upstream"], isolated, env)
        policy = _run([sys.executable, "-m", "rcdl006", "verify-policy-boundary"], isolated, env)
        output = Path(tmp) / "generated"
        tournament = _run([sys.executable, "-m", "rcdl006", "run", "--output", str(output)], isolated, env)
        manifest = _run([sys.executable, "-m", "rcdl006", "verify-manifest", str(output / "heldout-mechanism-manifest.json")], isolated, env)
        projection = _run([sys.executable, "-m", "rcdl006", "verify-projection", str(output / "verified-handoff-projection.json")], isolated, env)
        replay = Path(tmp) / "replay"
        replay_result = _run([sys.executable, "-m", "rcdl006", "run", "--output", str(replay)], isolated, env)
        deterministic = (
            tournament.returncode == 0
            and replay_result.returncode == 0
            and (output / "heldout-mechanism-results.jsonl").read_bytes()
            == (replay / "heldout-mechanism-results.jsonl").read_bytes()
        )
        probe = _run([sys.executable, "scripts/randomized_probe.py", "--samples", str(samples)], isolated, env)
        try:
            probe_document = json.loads(probe.stdout.strip())
        except json.JSONDecodeError:
            probe_document = {"comparisons": 0, "mismatches": -1, "status": "FAIL"}
        pass_codes = all(
            item.returncode == 0
            for item in (compile_result, tests, fixtures, upstream, policy, tournament, manifest, projection, replay_result, probe)
        )
        passed = pass_codes and deterministic and test_count >= 35 and probe_document.get("mismatches") == 0
        return {
            "compileall": "PASS" if compile_result.returncode == 0 else "FAIL",
            "deterministic_replay": "PASS" if deterministic else "FAIL",
            "fixture_boundary": "PASS" if fixtures.returncode == 0 else "FAIL",
            "isolated_copy": "PASS" if pass_codes else "FAIL",
            "manifest_projection": "PASS" if manifest.returncode == projection.returncode == 0 else "FAIL",
            "policy_boundary": "PASS" if policy.returncode == 0 else "FAIL",
            "randomized_probe": probe_document,
            "schema": "rcdl.release-check/0.6",
            "unit_tests": {"status": "PASS" if tests.returncode == 0 else "FAIL", "test_count": test_count},
            "upstream_boundary": "PASS" if upstream.returncode == 0 else "FAIL",
            "verdict": "PASS" if passed else "FAIL",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=384)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = release_check(args.samples)
    if args.output:
        write_canonical(args.output, result)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
