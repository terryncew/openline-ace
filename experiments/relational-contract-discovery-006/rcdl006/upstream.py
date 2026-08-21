"""Bind the experiment to a frozen EnvHarness core source surface."""

from __future__ import annotations

import hashlib
import inspect
import subprocess
from pathlib import Path
from typing import Any

from .canonical import load_json

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_upstream(reference_path: str | Path | None = None) -> dict[str, Any]:
    reference = load_json(
        reference_path or EXPERIMENT_ROOT / "references" / "envharness-upstream.json"
    )
    if not isinstance(reference, dict):
        raise ValueError("upstream reference must be an object")
    if (
        set(reference) != {
            "commit", "license", "license_sha256", "repository", "schema",
            "source_sha256",
        }
        or reference.get("schema") != "rcdl.envharness-upstream/0.6"
        or reference.get("repository") != "https://github.com/google-research/envharness"
        or reference.get("license") != "Apache-2.0"
        or len(str(reference.get("commit", ""))) != 40
    ):
        raise ValueError("upstream identity boundary failed")

    import envharness.core.actionable_env as actionable_module
    import envharness.core.envharness as harness_module
    import envharness.core.types as types_module
    import envharness.harnesses.rules as rules_module
    import envharness.harnesses.setup as setup_module
    from envharness import ActionableEnv, Rules

    modules = {
        "envharness/core/actionable_env.py": actionable_module,
        "envharness/core/envharness.py": harness_module,
        "envharness/core/types.py": types_module,
        "envharness/harnesses/rules.py": rules_module,
        "envharness/harnesses/setup.py": setup_module,
    }
    observed: dict[str, str] = {}
    roots: set[Path] = set()
    expected = reference.get("source_sha256")
    if not isinstance(expected, dict) or set(expected) != set(modules):
        raise ValueError("upstream source closure failed")
    for relative, module in modules.items():
        module_path = Path(inspect.getsourcefile(module) or "")
        if not module_path.is_file():
            raise ValueError(f"upstream module unavailable: {relative}")
        roots.add(module_path.resolve().parents[2])
        observed[relative] = _sha256(module_path)
        if observed[relative] != expected[relative]:
            raise ValueError(f"upstream source mismatch: {relative}")
    if len(roots) != 1:
        raise ValueError("upstream modules do not share one source checkout")
    source_root = roots.pop()
    license_path = source_root / "LICENSE"
    if not license_path.is_file() or _sha256(license_path) != reference["license_sha256"]:
        raise ValueError("upstream license boundary failed")
    git_result = subprocess.run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    if git_result.returncode != 0 or git_result.stdout.strip() != reference["commit"]:
        raise ValueError("upstream git commit boundary failed")

    required_env = {"reset", "step", "observe", "evaluate", "get_env_state", "save_state", "from_state"}
    required_rules = {"filter_action", "modify_transition", "filter_observation"}
    if not required_env.issubset(set(dir(ActionableEnv))) or not required_rules.issubset(set(dir(Rules))):
        raise ValueError("upstream interface boundary failed")
    return {
        "commit": reference["commit"],
        "interface": "ActionableEnv+Rules",
        "source_files": len(observed),
        "verified": True,
    }
