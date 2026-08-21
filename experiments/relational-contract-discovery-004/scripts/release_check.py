#!/usr/bin/env python3
"""Orthogonal release checks for RCDL-004."""

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
EXPERIMENTS = ROOT.parent
ENGINE_ROOT = EXPERIMENTS / "relational-contract-discovery-001"
SOURCE_ROOT = EXPERIMENTS / "relational-contract-discovery-003"
FROZEN_OUTPUT = ROOT / "evidence" / "pressure-test"


def environment(root: Path, *, include_source_package: bool = False) -> dict[str, str]:
    value = dict(os.environ)
    items = [root.parent / "relational-contract-discovery-001"]
    if include_source_package:
        items.append(root.parent / "relational-contract-discovery-003")
    items.append(root)
    value["PYTHONPATH"] = os.pathsep.join(str(item) for item in items)
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--probe-samples", type=int, default=128)
    args = parser.parse_args()
    if not 1 <= args.probe_samples <= 1_824:
        raise ValueError("probe samples must be in [1, 1824]")
    if not ENGINE_ROOT.is_dir() or not SOURCE_ROOT.is_dir() or not FROZEN_OUTPUT.is_dir():
        raise RuntimeError("frozen RCDL source or pressure-test evidence is missing")
    env = environment(ROOT)
    results: dict[str, object] = {}
    run([sys.executable, "-m", "compileall", "-q", "rcdl004", "tests", "scripts"], env=env)
    results["compileall"] = "PASS"
    results["source_bindings"] = json.loads(
        run([sys.executable, "-m", "rcdl004", "verify-bindings"], env=env)
    )
    regeneration = run(
        [sys.executable, "scripts/freeze_corpus.py", "--check"],
        env=environment(ROOT, include_source_package=True),
    )
    results["corpus_regeneration"] = json.loads(regeneration)
    test_output = run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        env=env,
    )
    results["unit_tests"] = {
        "status": "PASS",
        "test_count": test_output.count(" ... ok"),
        "skipped_count": test_output.count(" ... skipped"),
    }
    frozen_manifest = json.loads(
        run(
            [sys.executable, "-m", "rcdl004", "verify-manifest", str(FROZEN_OUTPUT / "pressure-test-manifest.json")],
            env=env,
        )
    )
    frozen_projection = json.loads(
        run(
            [sys.executable, "-m", "rcdl004", "verify-projection", str(FROZEN_OUTPUT / "contract-projection.json")],
            env=env,
        )
    )
    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        fresh = temp / "fresh-pressure-test"
        run([sys.executable, "-m", "rcdl004", "run", "--output", str(fresh)], env=env)
        run(
            [sys.executable, "-m", "rcdl004", "verify-manifest", str(fresh / "pressure-test-manifest.json")],
            env=env,
        )
        run(
            [sys.executable, "-m", "rcdl004", "verify-projection", str(fresh / "contract-projection.json")],
            env=env,
        )
        compared = (
            "predictions.jsonl",
            "pressure-test-manifest.json",
            "pressure-test-manifest.json.sha256",
            "contract-projection.json",
            "contract-projection.json.sha256",
            "summary.json",
        )
        for name in compared:
            if (fresh / name).read_bytes() != (FROZEN_OUTPUT / name).read_bytes():
                raise RuntimeError(f"fresh replay changed frozen bytes: {name}")
        results["deterministic_replay"] = {
            "status": "PASS",
            "byte_deterministic": True,
            "compared_file_count": len(compared),
            "manifest_sha256": _sha256(fresh / "pressure-test-manifest.json"),
            "prediction_sha256": _sha256(fresh / "predictions.jsonl"),
        }
        probe = run(
            [sys.executable, "scripts/randomized_probe.py", "--samples", str(args.probe_samples)],
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
        import_output = run(
            [
                sys.executable,
                "-c",
                "import importlib.util; assert importlib.util.find_spec('rcdl003') is None; import rcdl004.tournament",
            ],
            cwd=isolated,
            env=isolated_env,
        )
        if import_output:
            raise RuntimeError("unexpected isolated import output")
        run([sys.executable, "-m", "rcdl004", "verify-bindings"], cwd=isolated, env=isolated_env)
        run(
            [sys.executable, "-m", "rcdl004", "verify-manifest", "evidence/pressure-test/pressure-test-manifest.json"],
            cwd=isolated,
            env=isolated_env,
        )
        results["isolated_copy"] = {
            "status": "PASS",
            "outside_repository_context": True,
            "rcdl003_runtime_importable": False,
            "source_files_available_for_hash_binding_only": True,
        }
    results["frozen_manifest"] = frozen_manifest
    results["frozen_projection"] = frozen_projection
    results["claim_boundary"] = {
        "ace_level": "1_CANDIDATE",
        "promotion_authorized": False,
        "scientific_verdict": "LEARNED_PARITY",
        "same_builder": True,
        "independent_developer_or_lab": False,
        "neural_models_tested": False,
        "stochastic_llm_transport": "NOT_TESTED",
        "causal_equivalence": "NOT_ESTABLISHED",
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

