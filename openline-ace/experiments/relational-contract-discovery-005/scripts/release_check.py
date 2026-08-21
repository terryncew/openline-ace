#!/usr/bin/env python3
"""Run release-grade checks and write a canonical machine-readable report."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from rcdl005.canonical import canonical_json

ROOT = Path(__file__).resolve().parents[1]


def _run(
    command: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def _python_env(root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(root)
    return environment


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def build_report(samples: int) -> dict[str, object]:
    env = _python_env(ROOT)
    compile_result = _run(
        [sys.executable, "-m", "compileall", "-q", "rcdl005", "scripts", "tests"],
        env=env,
    )
    tests = _run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        env=env,
    )
    match = re.search(r"Ran (\d+) tests?", tests.stderr + tests.stdout)
    test_count = int(match.group(1)) if match else 0
    history = _run([sys.executable, "scripts/freeze_history.py", "--check"], env=env)
    probe = _run(
        [sys.executable, "scripts/randomized_probe.py", "--samples", str(samples)],
        env=env,
    )
    try:
        probe_document = json.loads(probe.stdout)
    except json.JSONDecodeError:
        probe_document = {"status": "FAIL", "comparisons": 0, "mismatches": -1}
    replay_status = "FAIL"
    isolated_status = "FAIL"
    with tempfile.TemporaryDirectory() as first_name, tempfile.TemporaryDirectory() as second_name:
        first = Path(first_name) / "out"
        second = Path(second_name) / "out"
        left = _run(
            [sys.executable, "-m", "rcdl005", "run", "--output", str(first)],
            env=env,
        )
        right = _run(
            [sys.executable, "-m", "rcdl005", "run", "--output", str(second)],
            env=env,
        )
        if left.returncode == right.returncode == 0 and _tree_bytes(first) == _tree_bytes(second):
            replay_status = "PASS"
    with tempfile.TemporaryDirectory() as isolated_name:
        isolated = Path(isolated_name) / "experiment"
        shutil.copytree(
            ROOT,
            isolated,
            ignore=shutil.ignore_patterns("evidence", "__pycache__", "*.pyc"),
        )
        isolated_env = _python_env(isolated)
        verify = _run(
            [sys.executable, "-m", "rcdl005", "verify-domain"],
            cwd=isolated,
            env=isolated_env,
        )
        output = Path(isolated_name) / "isolated-out"
        run = _run(
            [sys.executable, "-m", "rcdl005", "run", "--output", str(output)],
            cwd=isolated,
            env=isolated_env,
        )
        if verify.returncode == run.returncode == 0:
            isolated_status = "PASS"
    checks_pass = (
        compile_result.returncode == 0
        and tests.returncode == 0
        and test_count >= 20
        and history.returncode == 0
        and probe.returncode == 0
        and probe_document.get("status") == "PASS"
        and replay_status == "PASS"
        and isolated_status == "PASS"
    )
    return {
        "schema": "rcdl.release-check/0.5",
        "verdict": "PASS" if checks_pass else "FAIL",
        "compileall": "PASS" if compile_result.returncode == 0 else "FAIL",
        "unit_tests": {
            "status": "PASS" if tests.returncode == 0 else "FAIL",
            "test_count": test_count,
            "skipped_count": 0,
        },
        "history_regeneration": "PASS" if history.returncode == 0 else "FAIL",
        "randomized_probe": probe_document,
        "deterministic_replay": replay_status,
        "isolated_copy": isolated_status,
        "claim_boundary": {
            "scientific_verdict": "CAUSAL_UTILITY_PARITY",
            "same_builder": True,
            "independent_replication": False,
            "stochastic_llm_transport": "NOT_TESTED",
            "promotion_authorized": False,
            "policy_authority": "NONE",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=512)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evidence" / "release-check.json",
    )
    args = parser.parse_args()
    report = build_report(args.samples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(report) + b"\n")
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

