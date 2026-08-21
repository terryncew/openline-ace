from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from .canonical import git_blob_sha1


def experiment_root() -> Path:
    return Path(__file__).resolve().parents[1]


def repo_root() -> Path:
    here = experiment_root()
    for parent in [here, *here.parents]:
        probe = parent / "experiments" / "agent-contract-audit-001" / "aca001" / "audit.py"
        if probe.exists():
            return parent
    raise RuntimeError("cannot locate frozen agent-contract-audit-001 sibling")


def verify_a001_pin() -> dict[str, str]:
    root = experiment_root()
    pin = json.loads((root / "upstream_pin.json").read_text(encoding="utf-8"))
    source = repo_root() / pin["source"]
    observed: dict[str, str] = {}
    for name, expected in pin["git_blob_sha1"].items():
        path = source / name
        if not path.exists():
            raise RuntimeError(f"missing frozen A-001 source: {name}")
        actual = git_blob_sha1(path.read_bytes())
        if actual != expected:
            raise RuntimeError(f"A-001 source drift: {name}: {actual} != {expected}")
        observed[name] = actual
    return observed


def load_a001():
    verify_a001_pin()
    sibling = repo_root() / "experiments" / "agent-contract-audit-001"
    value = str(sibling)
    if value not in sys.path:
        sys.path.insert(0, value)
    model = importlib.import_module("aca001.model")
    audit = importlib.import_module("aca001.audit")
    return model, audit
