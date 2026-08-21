"""Pinned external-model identity and claim-boundary verification."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import canonical_digest, load_json_bytes

REFERENCE_SCHEMA = "rcdl.external-reference/0.1"
EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORD = EXPERIMENT_ROOT / "references" / "official_raft_reference.json"


class ReferenceVerificationError(ValueError):
    pass


@dataclass(frozen=True)
class ReferenceVerification:
    record_digest: str
    content_sha256: str
    git_blob_sha1: str
    execution_binding: str
    tlc_execution: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": True,
            "record_digest": self.record_digest,
            "content_sha256": self.content_sha256,
            "git_blob_sha1": self.git_blob_sha1,
            "execution_binding": self.execution_binding,
            "tlc_execution": self.tlc_execution,
        }


def load_reference_record(path: str | Path = DEFAULT_RECORD) -> dict[str, Any]:
    value = load_json_bytes(Path(path).read_bytes())
    if not isinstance(value, dict):
        raise ReferenceVerificationError("reference record must be an object")
    expected_keys = {
        "schema",
        "name",
        "repository",
        "commit",
        "path",
        "git_blob_sha1",
        "sha256",
        "paper",
        "mapped_safety_properties",
        "execution_binding",
        "tlc_execution",
    }
    if set(value) != expected_keys:
        raise ReferenceVerificationError("reference record closure failed")
    if value["schema"] != REFERENCE_SCHEMA:
        raise ReferenceVerificationError("unsupported reference schema")
    if value["repository"] != "https://github.com/ongardie/raft.tla":
        raise ReferenceVerificationError("unexpected Raft reference repository")
    if value["path"] != "raft.tla":
        raise ReferenceVerificationError("Raft reference path must be the pinned local file")
    if not isinstance(value["commit"], str) or not re.fullmatch(r"[0-9a-f]{40}", value["commit"]):
        raise ReferenceVerificationError("invalid reference commit")
    if not isinstance(value["git_blob_sha1"], str) or not re.fullmatch(
        r"[0-9a-f]{40}", value["git_blob_sha1"]
    ):
        raise ReferenceVerificationError("invalid reference Git blob")
    if not isinstance(value["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", value["sha256"]):
        raise ReferenceVerificationError("invalid reference SHA-256")
    if value["execution_binding"] != "PROPERTY_MAPPING_ONLY":
        raise ReferenceVerificationError("unexpected execution binding")
    if value["tlc_execution"] != "NOT_RUN":
        raise ReferenceVerificationError("unexpected TLC claim")
    return value


def verify_reference(path: str | Path = DEFAULT_RECORD) -> ReferenceVerification:
    record_path = Path(path)
    record = load_reference_record(record_path)
    content_path = record_path.parent / record["path"]
    payload = content_path.read_bytes()
    content_sha256 = hashlib.sha256(payload).hexdigest()
    blob_header = f"blob {len(payload)}\0".encode("ascii")
    git_blob_sha1 = hashlib.sha1(blob_header + payload).hexdigest()
    if content_sha256 != record["sha256"]:
        raise ReferenceVerificationError("pinned Raft SHA-256 mismatch")
    if git_blob_sha1 != record["git_blob_sha1"]:
        raise ReferenceVerificationError("pinned Raft Git blob mismatch")
    return ReferenceVerification(
        record_digest=canonical_digest(record),
        content_sha256=content_sha256,
        git_blob_sha1=git_blob_sha1,
        execution_binding=record["execution_binding"],
        tlc_execution=record["tlc_execution"],
    )
