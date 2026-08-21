#!/usr/bin/env python3
"""Orthogonal release checks for RCDL-002."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE_ROOT = ROOT.parent / "relational-contract-discovery-001"


def run(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n{completed.stdout}"
        )
    return completed.stdout


def environment(root: Path) -> dict[str, str]:
    value = dict(os.environ)
    engine_root = root.parent / "relational-contract-discovery-001"
    value["PYTHONPATH"] = os.pathsep.join((str(engine_root), str(root)))
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--probe-seeds", type=int, default=256)
    args = parser.parse_args()
    if not 1 <= args.probe_seeds <= 10_000:
        raise ValueError("probe seeds must be in [1, 10000]")
    if not ENGINE_ROOT.is_dir():
        raise RuntimeError("frozen RCDL-001 engine directory is missing")

    results: dict[str, object] = {}
    env = environment(ROOT)
    run([sys.executable, "-m", "compileall", "-q", "rcdl002", "tests", "scripts"], env=env)
    results["compileall"] = "PASS"
    engine_output = run([sys.executable, "-m", "rcdl002", "verify-engine"], env=env)
    results["engine_reference"] = json.loads(engine_output)
    test_output = run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        env=env,
    )
    results["unit_tests"] = {
        "status": "PASS",
        "test_count": test_output.count(" ... ok"),
        "skipped_count": test_output.count(" ... skipped"),
    }

    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        first = temp / "calibration-a"
        second = temp / "calibration-b"
        for output in (first, second):
            run(
                [
                    sys.executable,
                    "-m",
                    "rcdl002",
                    "calibrate",
                    "--output",
                    str(output),
                    "--trials",
                    "8",
                ],
                env=env,
            )
            run(
                [sys.executable, "-m", "rcdl002", "verify-manifest", str(output / "contract-manifest.json")],
                env=env,
            )
            run(
                [sys.executable, "-m", "rcdl002", "verify-projection", str(output / "contract-projection.json")],
                env=env,
            )
        manifest = (first / "contract-manifest.json").read_bytes()
        projection = (first / "contract-projection.json").read_bytes()
        if manifest != (second / "contract-manifest.json").read_bytes():
            raise RuntimeError("manifest replay was not byte deterministic")
        if projection != (second / "contract-projection.json").read_bytes():
            raise RuntimeError("projection replay was not byte deterministic")
        results["calibration"] = {
            "status": "PASS",
            "trials_per_arm": 8,
            "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
            "projection_sha256": hashlib.sha256(projection).hexdigest(),
            "deterministic_replay": True,
        }

        probe_output = run(
            [
                sys.executable,
                "scripts/randomized_probe.py",
                "--seeds",
                str(args.probe_seeds),
            ],
            env=env,
        )
        results["randomized_probe"] = json.loads(probe_output)

        isolated_parent = temp / "isolated" / "experiments"
        isolated_parent.mkdir(parents=True)
        isolated_engine = isolated_parent / ENGINE_ROOT.name
        isolated = isolated_parent / ROOT.name
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
        shutil.copytree(ENGINE_ROOT, isolated_engine, ignore=ignore)
        shutil.copytree(ROOT, isolated, ignore=ignore)
        isolated_env = environment(isolated)
        isolated_tests = run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=isolated,
            env=isolated_env,
        )
        isolated_output = temp / "isolated-calibration"
        run(
            [
                sys.executable,
                "-m",
                "rcdl002",
                "calibrate",
                "--output",
                str(isolated_output),
                "--trials",
                "2",
            ],
            cwd=isolated,
            env=isolated_env,
        )
        results["isolated_copy"] = {
            "status": "PASS",
            "test_count": isolated_tests.count(" ... ok"),
            "outside_repository_context": True,
            "engine_sibling_copied": True,
        }

    results["claim_boundary"] = {
        "ace_level": "1_CANDIDATE",
        "promotion_authorized": False,
        "independent_implementation": "NOT_TESTED",
        "stochastic_llm_transport": "NOT_TESTED",
    }
    results["verdict"] = "PASS"
    payload = json.dumps(results, sort_keys=True, separators=(",", ":")) + "\n"
    if args.evidence:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
