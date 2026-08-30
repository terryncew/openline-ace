from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Any


def file_sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_task(experiment_root: pathlib.Path) -> dict[str, Any]:
    return json.loads((experiment_root / "EXTERNAL_TASK.json").read_text())


def verify_local_artifacts(experiment_root: pathlib.Path, task: dict[str, Any]) -> dict[str, Any]:
    expected = {
        task["oracle"]["test_patch_file"]: task["oracle"]["test_patch_sha256"],
        task["historical_fix"]["patch_file"]: task["historical_fix"]["patch_sha256"],
        task["environment"]["lock_file"]: task["environment"]["lock_sha256"],
    }
    rows = []
    for rel, wanted in expected.items():
        path = experiment_root / rel
        got = file_sha256(path) if path.exists() else None
        rows.append({"path": rel, "expected": wanted, "observed": got, "matched": got == wanted})
    return {"passed": all(row["matched"] for row in rows), "artifacts": rows}


def _run(
    command: list[str],
    *,
    cwd: pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 300,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}\n{result.stdout[-4000:]}")
    return result


def install_environment(experiment_root: pathlib.Path, task: dict[str, Any]) -> dict[str, Any]:
    lock = experiment_root / task["environment"]["lock_file"]
    result = _run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--quiet",
            "-r",
            str(lock),
        ],
        timeout=600,
    )
    return {
        "passed": result.returncode == 0,
        "returncode": result.returncode,
        "output_tail": result.stdout[-2000:],
    }


def materialize_source(destination: pathlib.Path, task: dict[str, Any]) -> dict[str, Any]:
    if destination.exists():
        raise FileExistsError(destination)
    destination.mkdir(parents=True)
    _run(["git", "init", "--quiet"], cwd=destination, check=True)
    _run(["git", "remote", "add", "origin", task["repository_url"]], cwd=destination, check=True)
    _run(
        ["git", "fetch", "--quiet", "--depth=1", "origin", task["base_commit"]],
        cwd=destination,
        timeout=600,
        check=True,
    )
    _run(["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"], cwd=destination, check=True)
    head = _run(["git", "rev-parse", "HEAD"], cwd=destination, check=True).stdout.strip()
    source_rows = []
    for rel, expected in task["source_files"].items():
        path = destination / rel
        observed = file_sha256(path) if path.exists() else None
        source_rows.append(
            {"path": rel, "expected": expected, "observed": observed, "matched": observed == expected}
        )
    clean = not _run(["git", "status", "--porcelain"], cwd=destination, check=True).stdout.strip()
    return {
        "head": head,
        "head_matched": head == task["base_commit"],
        "source_hashes": source_rows,
        "source_hashes_matched": all(row["matched"] for row in source_rows),
        "clean": clean,
    }


def apply_patch(repo: pathlib.Path, patch_path: pathlib.Path) -> None:
    _run(["git", "apply", "--check", str(patch_path)], cwd=repo, check=True)
    _run(["git", "apply", str(patch_path)], cwd=repo, check=True)


def prepare_candidate(
    source: pathlib.Path,
    destination: pathlib.Path,
    experiment_root: pathlib.Path,
    task: dict[str, Any],
    candidate_patch: str | None,
) -> pathlib.Path:
    shutil.copytree(source, destination, symlinks=True)
    apply_patch(destination, experiment_root / task["oracle"]["test_patch_file"])
    if candidate_patch is not None:
        apply_patch(destination, experiment_root / candidate_patch)
    return destination


def run_pytest(repo: pathlib.Path, selectors: list[str], *, timeout: int = 300) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo / "src")
    env["PYTHONWARNINGS"] = "ignore::DeprecationWarning"
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-W",
        "ignore::DeprecationWarning",
        "-q",
        *selectors,
    ]
    result = _run(command, cwd=repo, env=env, timeout=timeout)
    return {
        "command": command,
        "passed": result.returncode == 0,
        "returncode": result.returncode,
        "output_tail": result.stdout[-6000:],
    }


def evaluate_candidate(
    source: pathlib.Path,
    work_root: pathlib.Path,
    experiment_root: pathlib.Path,
    task: dict[str, Any],
    *,
    name: str,
    candidate_patch: str | None,
) -> dict[str, Any]:
    repo = prepare_candidate(source, work_root / name, experiment_root, task, candidate_patch)
    target = run_pytest(repo, list(task["oracle"]["fail_to_pass"]))
    consequence = run_pytest(repo, list(task["oracle"]["consequence_command"]))
    changed_paths = sorted(
        line for line in _run(["git", "diff", "--name-only"], cwd=repo, check=True).stdout.splitlines() if line
    )
    diff = _run(["git", "diff", "--binary"], cwd=repo, check=True).stdout
    return {
        "name": name,
        "candidate_patch": candidate_patch,
        "target": target,
        "consequence": consequence,
        "changed_paths_with_oracle": changed_paths,
        "working_diff_sha256": hashlib.sha256(diff.encode()).hexdigest(),
    }


def python_matches(task: dict[str, Any]) -> bool:
    expected = tuple(int(part) for part in task["environment"]["python"].split("."))
    return sys.version_info[:2] == expected
