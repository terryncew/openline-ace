"""Verify frozen corpus sources, clauses, engine, and import boundaries."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rcdl.canonical import canonical_digest, load_json_bytes
from rcdl.model import Clause

from .corpus import MANIFEST_PATH, load_frozen_corpus

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]


class BindingVerificationError(ValueError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_digest(value: Any, length: int = 64) -> bool:
    return isinstance(value, str) and len(value) == length and all(
        character in "0123456789abcdef" for character in value
    )


@dataclass(frozen=True)
class BindingVerification:
    corpus_payload_sha256: str
    source_aggregate_sha256: str
    engine_aggregate_sha256: str
    clause_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": True,
            "corpus_payload_sha256": self.corpus_payload_sha256,
            "source_aggregate_sha256": self.source_aggregate_sha256,
            "engine_aggregate_sha256": self.engine_aggregate_sha256,
            "clause_count": self.clause_count,
            "rcdl003_runtime_imports": False,
            "raw_identity_features": False,
        }


def _verify_engine(source_root: Path, record: dict[str, Any]) -> str:
    if set(record) != {"path", "sha256"}:
        raise BindingVerificationError("engine-reference record closure failed")
    reference_path = (source_root / record["path"]).resolve()
    if source_root not in reference_path.parents or _sha256(reference_path) != record["sha256"]:
        raise BindingVerificationError("engine-reference bytes changed")
    reference = load_json_bytes(reference_path.read_bytes())
    if not isinstance(reference, dict) or reference.get("schema") != "rcdl.engine-reference/0.1":
        raise BindingVerificationError("engine-reference schema failed")
    engine_root = (source_root / reference["source_experiment"]).resolve()
    observed: list[dict[str, str]] = []
    for item in reference.get("files", []):
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise BindingVerificationError("engine file record failed")
        path = (engine_root / item["path"]).resolve()
        if engine_root not in path.parents or not path.is_file() or _sha256(path) != item["sha256"]:
            raise BindingVerificationError(f"frozen engine changed: {item.get('path')}")
        observed.append({"path": item["path"], "sha256": item["sha256"]})
    aggregate = canonical_digest(observed)
    if aggregate != reference.get("aggregate_sha256"):
        raise BindingVerificationError("engine aggregate changed")
    return aggregate


def _verify_import_boundary() -> None:
    for path in sorted((EXPERIMENT_ROOT / "rcdl004").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            if any(name == "rcdl003" or name.startswith("rcdl003.") for name in names):
                raise BindingVerificationError(f"runtime imports RCDL-003: {path.name}")


def verify_frozen_bindings() -> BindingVerification:
    corpus = load_frozen_corpus()
    manifest = load_json_bytes(MANIFEST_PATH.read_bytes())
    if not isinstance(manifest, dict):
        raise BindingVerificationError("corpus manifest is invalid")
    bindings = manifest.get("source_bindings")
    if not isinstance(bindings, dict) or set(bindings) != {
        "repository_commit", "source_experiment", "source_files", "clauses", "engine_reference"
    }:
        raise BindingVerificationError("source binding closure failed")
    if not _is_digest(bindings["repository_commit"], 40):
        raise BindingVerificationError("source commit is invalid")
    source_root = (EXPERIMENT_ROOT / bindings["source_experiment"]).resolve()
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in bindings["source_files"]:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"} or item["path"] in seen:
            raise BindingVerificationError("source file record failed")
        seen.add(item["path"])
        path = (source_root / item["path"]).resolve()
        if source_root not in path.parents or not path.is_file() or _sha256(path) != item["sha256"]:
            raise BindingVerificationError(f"frozen source changed: {item['path']}")
        records.append({"path": item["path"], "sha256": item["sha256"]})
    clause_count = 0
    for item in bindings["clauses"]:
        if not isinstance(item, dict) or set(item) != {"path", "file_sha256"}:
            raise BindingVerificationError("clause binding record failed")
        path = (source_root / item["path"]).resolve()
        if source_root not in path.parents or _sha256(path) != item["file_sha256"]:
            raise BindingVerificationError(f"frozen clause changed: {item['path']}")
        Clause.from_path(path)
        records.append({"path": item["path"], "sha256": item["file_sha256"]})
        clause_count += 1
    if clause_count != 5:
        raise BindingVerificationError("expected five frozen clauses")
    engine_aggregate = _verify_engine(source_root, bindings["engine_reference"])
    _verify_import_boundary()
    return BindingVerification(
        corpus.payload_sha256,
        canonical_digest(records),
        engine_aggregate,
        clause_count,
    )

