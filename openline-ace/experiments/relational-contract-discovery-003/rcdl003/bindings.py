"""Fail-closed verification of frozen engines, clauses, traces, and code paths."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rcdl.canonical import canonical_digest, load_json_bytes
from rcdl.model import Clause

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
ENGINE_REFERENCE = EXPERIMENT_ROOT / "references" / "rcdl_0_1_engine_reference.json"
REPLICATION_REFERENCE = (
    EXPERIMENT_ROOT / "references" / "frozen_replication_reference.json"
)


class BindingVerificationError(ValueError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_commit(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


@dataclass(frozen=True)
class BindingVerification:
    engine_aggregate_sha256: str
    engine_file_count: int
    clause_count: int
    source_trace_count: int
    source_implementation_sha256: str
    replica_implementation_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": True,
            "engine_aggregate_sha256": self.engine_aggregate_sha256,
            "engine_file_count": self.engine_file_count,
            "clause_count": self.clause_count,
            "source_trace_count": self.source_trace_count,
            "source_implementation_sha256": self.source_implementation_sha256,
            "replica_implementation_sha256": self.replica_implementation_sha256,
            "no_rcdl002_runtime_imports": True,
            "code_path_independent": True,
            "independent_developer_or_lab": False,
        }


def _verify_engine() -> tuple[str, int]:
    reference = load_json_bytes(ENGINE_REFERENCE.read_bytes())
    if not isinstance(reference, dict) or set(reference) != {
        "schema",
        "name",
        "repository_commit",
        "source_experiment",
        "aggregate_sha256",
        "files",
    }:
        raise BindingVerificationError("engine reference closure failed")
    if reference["schema"] != "rcdl.engine-reference/0.1" or not _is_commit(
        reference["repository_commit"]
    ):
        raise BindingVerificationError("engine reference header is invalid")
    source_root = (EXPERIMENT_ROOT / reference["source_experiment"]).resolve()
    observed: list[dict[str, str]] = []
    files = reference["files"]
    if not isinstance(files, list) or not files:
        raise BindingVerificationError("engine reference has no files")
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise BindingVerificationError("invalid engine file record")
        path = (source_root / item["path"]).resolve()
        if source_root not in path.parents or not path.is_file():
            raise BindingVerificationError("engine file missing or outside source root")
        digest = _sha256(path)
        if digest != item["sha256"]:
            raise BindingVerificationError(f"frozen engine changed: {item['path']}")
        observed.append({"path": item["path"], "sha256": digest})
    aggregate = canonical_digest(observed)
    if aggregate != reference["aggregate_sha256"]:
        raise BindingVerificationError("engine aggregate digest mismatch")
    return aggregate, len(observed)


def _verify_no_source_imports() -> None:
    for path in sorted((EXPERIMENT_ROOT / "rcdl003").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            if any(name == "rcdl002" or name.startswith("rcdl002.") for name in names):
                raise BindingVerificationError(f"RCDL-003 imports source code: {path.name}")


def verify_frozen_bindings() -> BindingVerification:
    reference = load_json_bytes(REPLICATION_REFERENCE.read_bytes())
    if not isinstance(reference, dict) or set(reference) != {
        "schema",
        "source_experiment",
        "source_repository_commit",
        "source_feature_commit",
        "source_implementation",
        "clauses",
        "source_baseline_traces",
    }:
        raise BindingVerificationError("replication reference closure failed")
    if (
        reference["schema"] != "rcdl.frozen-replication-reference/0.1"
        or not _is_commit(reference["source_repository_commit"])
        or not _is_commit(reference["source_feature_commit"])
    ):
        raise BindingVerificationError("replication reference header is invalid")
    source_root = (EXPERIMENT_ROOT / reference["source_experiment"]).resolve()
    source_record = reference["source_implementation"]
    if not isinstance(source_record, dict) or set(source_record) != {"path", "sha256"}:
        raise BindingVerificationError("source implementation record is invalid")
    source_path = (source_root / source_record["path"]).resolve()
    if source_root not in source_path.parents or _sha256(source_path) != source_record["sha256"]:
        raise BindingVerificationError("source implementation binding failed")

    clauses = reference["clauses"]
    if not isinstance(clauses, list) or len(clauses) != 5:
        raise BindingVerificationError("frozen clause reference must contain five clauses")
    seen: set[str] = set()
    for item in clauses:
        if not isinstance(item, dict) or set(item) != {
            "path",
            "file_sha256",
            "clause_digest",
        }:
            raise BindingVerificationError("frozen clause record is invalid")
        if item["path"] in seen:
            raise BindingVerificationError("duplicate frozen clause path")
        seen.add(item["path"])
        path = EXPERIMENT_ROOT / "clauses" / item["path"]
        if _sha256(path) != item["file_sha256"]:
            raise BindingVerificationError(f"frozen clause bytes changed: {item['path']}")
        if Clause.from_path(path).digest != item["clause_digest"]:
            raise BindingVerificationError(f"frozen clause semantics changed: {item['path']}")

    trace_records = reference["source_baseline_traces"]
    if not isinstance(trace_records, list) or len(trace_records) != 10:
        raise BindingVerificationError("source baseline must contain ten traces")
    trace_names: set[str] = set()
    for item in trace_records:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise BindingVerificationError("source trace record is invalid")
        if item["path"] in trace_names:
            raise BindingVerificationError("duplicate source trace path")
        trace_names.add(item["path"])
        path = EXPERIMENT_ROOT / "references" / "source-baseline" / item["path"]
        if _sha256(path) != item["sha256"]:
            raise BindingVerificationError(f"source trace changed: {item['path']}")

    _verify_no_source_imports()
    replica_digest = _sha256(EXPERIMENT_ROOT / "rcdl003" / "replica.py")
    if replica_digest == source_record["sha256"]:
        raise BindingVerificationError("replica implementation equals source bytes")
    engine_digest, engine_files = _verify_engine()
    return BindingVerification(
        engine_digest,
        engine_files,
        len(clauses),
        len(trace_records),
        source_record["sha256"],
        replica_digest,
    )
