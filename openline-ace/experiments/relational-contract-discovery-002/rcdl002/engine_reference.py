"""Verify that RCDL-002 is using the frozen RCDL 0.1 engine unchanged."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rcdl.canonical import canonical_digest, load_json_bytes

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = EXPERIMENT_ROOT / "references" / "rcdl_0_1_engine_reference.json"


class EngineReferenceError(ValueError):
    """Raised when the frozen RCDL 0.1 engine no longer matches its reference."""


@dataclass(frozen=True)
class EngineVerification:
    source_experiment: str
    repository_commit: str
    aggregate_sha256: str
    file_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": True,
            "source_experiment": self.source_experiment,
            "repository_commit": self.repository_commit,
            "aggregate_sha256": self.aggregate_sha256,
            "file_count": self.file_count,
            "engine_modified": False,
        }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_engine_reference(path: str | Path = REFERENCE_PATH) -> dict[str, Any]:
    value = load_json_bytes(Path(path).read_bytes())
    if not isinstance(value, dict):
        raise EngineReferenceError("engine reference must be an object")
    return value


def verify_engine_reference(path: str | Path = REFERENCE_PATH) -> EngineVerification:
    target = Path(path)
    reference = load_engine_reference(target)
    if set(reference) != {
        "schema",
        "name",
        "repository_commit",
        "source_experiment",
        "aggregate_sha256",
        "files",
    }:
        raise EngineReferenceError("engine reference top-level closure failed")
    if reference["schema"] != "rcdl.engine-reference/0.1":
        raise EngineReferenceError("unsupported engine reference schema")
    source_name = reference["source_experiment"]
    if not isinstance(source_name, str) or not source_name:
        raise EngineReferenceError("engine source experiment is invalid")
    source_root = (target.parent.parent / source_name).resolve()
    files = reference["files"]
    if not isinstance(files, list) or not files:
        raise EngineReferenceError("engine reference has no files")
    observed: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise EngineReferenceError("engine file record is invalid")
        relative = item["path"]
        expected = item["sha256"]
        if not isinstance(relative, str) or relative in seen:
            raise EngineReferenceError("engine file path is invalid or duplicated")
        seen.add(relative)
        candidate = (source_root / relative).resolve()
        if source_root not in candidate.parents or not candidate.is_file():
            raise EngineReferenceError(f"engine file is missing or escapes source root: {relative}")
        actual = _sha256(candidate)
        if actual != expected:
            raise EngineReferenceError(f"frozen engine file changed: {relative}")
        observed.append({"path": relative, "sha256": actual})
    aggregate = canonical_digest(observed)
    if aggregate != reference["aggregate_sha256"]:
        raise EngineReferenceError("engine aggregate digest mismatch")
    commit = reference["repository_commit"]
    if (
        not isinstance(commit, str)
        or len(commit) != 40
        or any(character not in "0123456789abcdef" for character in commit)
    ):
        raise EngineReferenceError("engine repository commit is invalid")
    return EngineVerification(source_name, commit, aggregate, len(observed))
