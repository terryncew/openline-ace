#!/usr/bin/env python3
"""Orthogonal release checks for RCDL-003."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT.parent
ENGINE_ROOT = EXPERIMENTS / "relational-contract-discovery-001"
SOURCE_ROOT = EXPERIMENTS / "relational-contract-discovery-002"


def environment(root: Path) -> dict[str, str]:
    value = dict(os.environ)
    engine = root.parent / "relational-contract-discovery-001"
    value["PYTHONPATH"] = os.pathsep.join((str(engine), str(root)))
    return value


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--probe-seeds", type=int, default=256)
    args = parser.parse_args()
    if not 1 <= args.probe_seeds <= 10_000:
        raise ValueError("probe seeds must be in [1, 10000]")
    if not ENGINE_ROOT.is_dir() or not SOURCE_ROOT.is_dir():
        raise RuntimeError("frozen RCDL source experiments are missing")
    env = environment(ROOT)
    results: dict[str, object] = {}
    run([sys.executable, "-m", "compileall", "-q", "rcdl003", "tests", "scripts"], env=env)
    results["compileall"] = "PASS"
    results["source_bindings"] = json.loads(
        run([sys.executable, "-m", "rcdl003", "verify-bindings"], env=env)
    )
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
        first = temp / "replication-a"
        second = temp / "replication-b"
        for output in (first, second):
            run(
                [
                    sys.executable,
                    "-m",
                    "rcdl003",
                    "run",
                    "--output",
                    str(output),
                    "--trials",
                    "8",
                ],
                env=env,
            )
            run(
                [sys.executable, "-m", "rcdl003", "verify-manifest", str(output / "contract-manifest.json")],
                env=env,
            )
            run(
                [sys.executable, "-m", "rcdl003", "verify-projection", str(output / "contract-projection.json")],
                env=env,
            )
        for name in ("contract-manifest.json", "contract-projection.json", "summary.json"):
            if (first / name).read_bytes() != (second / name).read_bytes():
                raise RuntimeError(f"replication replay changed bytes: {name}")
        results["deterministic_replay"] = {
            "status": "PASS",
            "byte_deterministic": True,
            "trials_per_arm": 8,
            "manifest_sha256": hashlib.sha256((first / "contract-manifest.json").read_bytes()).hexdigest(),
            "projection_sha256": hashlib.sha256((first / "contract-projection.json").read_bytes()).hexdigest(),
        }
        probe = run(
            [sys.executable, "scripts/randomized_probe.py", "--seeds", str(args.probe_seeds)],
            env=env,
        )
        results["randomized_probe"] = json.loads(probe)

        isolated_experiments = temp / "isolated" / "experiments"
        isolated_experiments.mkdir(parents=True)
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
        for source in (ENGINE_ROOT, SOURCE_ROOT, ROOT):
            shutil.copytree(source, isolated_experiments / source.name, ignore=ignore)
        isolated = isolated_experiments / ROOT.name
        isolated_env = environment(isolated)
        import_check = run(
            [
                sys.executable,
                "-c",
                (
                    "import importlib.util; "
                    "assert importlib.util.find_spec('rcdl002') is None; "
                    "import rcdl003.replica"
                ),
            ],
            cwd=isolated,
            env=isolated_env,
        )
        if import_check:
            raise RuntimeError("unexpected isolated import-check output")
        isolated_tests = run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=isolated,
            env=isolated_env,
        )
        isolated_output = temp / "isolated-replication"
        run(
            [
                sys.executable,
                "-m",
                "rcdl003",
                "run",
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
            "outside_repository_context": True,
            "test_count": isolated_tests.count(" ... ok"),
            "rcdl002_runtime_importable": False,
            "source_files_available_for_hash_binding_only": True,
        }
    results["claim_boundary"] = {
        "ace_level": "1_CANDIDATE",
        "promotion_authorized": False,
        "independent_code_path": True,
        "independent_developer_or_lab": False,
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
