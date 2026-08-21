"""Fail-closed verification for manifests and handoff projections."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import canonical_json, load_json_bytes


@dataclass(frozen=True)
class VerifiedDocument:
    path: Path
    digest: str
    document: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"verified": True, "path": str(self.path), "sha256": self.digest}


def _bound_document(path: Path) -> VerifiedDocument:
    payload = path.read_bytes()
    document = load_json_bytes(payload)
    if not isinstance(document, dict) or payload != canonical_json(document) + b"\n":
        raise ValueError(f"non-canonical document: {path}")
    digest = hashlib.sha256(payload).hexdigest()
    sidecar = path.with_suffix(path.suffix + ".sha256")
    parts = sidecar.read_text(encoding="utf-8").strip().split() if sidecar.is_file() else []
    if len(parts) != 2 or parts[0] != digest or parts[1] != path.name:
        raise ValueError(f"digest sidecar mismatch: {path}")
    return VerifiedDocument(path, digest, document)


def verify_manifest(path: str | Path) -> VerifiedDocument:
    verified = _bound_document(Path(path))
    document = verified.document
    if set(document) != {
        "schema",
        "tool_version",
        "experiment_id",
        "tournament_id",
        "ace",
        "tournament",
        "results",
        "claim_effect",
        "limitations",
        "verdict",
    }:
        raise ValueError("manifest closure failed")
    if (
        document["schema"] != "rcdl.causal-utility-manifest/0.5"
        or document["experiment_id"] != "relational-contract-discovery-005"
        or document["ace"]
        != {
            "level": "1_CANDIDATE",
            "promotion_authorized": False,
            "receipt_gate_authorization": "NONE",
        }
    ):
        raise ValueError("manifest authority boundary failed")
    tournament = document["tournament"]
    results = document["results"]
    if (
        not isinstance(tournament, dict)
        or tournament.get("schema") != "rcdl.causal-utility-tournament/0.5"
        or tournament.get("protocol_status") != "VALID_RESULT"
        or tournament.get("scientific_verdict") != "CAUSAL_UTILITY_PARITY"
        or not isinstance(results, dict)
        or results.get("schema") != "rcdl.causal-utility-result/0.5"
        or results.get("row_count") != 1024
        or document["claim_effect"]
        != "UNIQUE_CAUSAL_UTILITY_FALSIFIED_WITHIN_TOURNAMENT"
        or document["verdict"] != "CAUSAL_UTILITY_TEST_CAUSAL_UTILITY_PARITY"
    ):
        raise ValueError("manifest scientific boundary failed")
    results_path = verified.path.parent / str(results["path"])
    payload = results_path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != results["sha256"]:
        raise ValueError("result payload digest mismatch")
    lines = payload.splitlines()
    if len(lines) != results["row_count"]:
        raise ValueError("result payload row count mismatch")
    for line in lines:
        record = load_json_bytes(line)
        if not isinstance(record, dict) or line != canonical_json(record):
            raise ValueError("non-canonical result record")
        if record.get("schema") != results["schema"]:
            raise ValueError("result record schema mismatch")
    return verified


def verify_projection(path: str | Path) -> VerifiedDocument:
    verified = _bound_document(Path(path))
    document = verified.document
    if set(document) != {"schema", "projection_id", "source", "claim", "gate", "reopen_if"}:
        raise ValueError("projection closure failed")
    source = document["source"]
    gate = document["gate"]
    claim = document["claim"]
    if (
        document["schema"] != "openline.verified-handoff-projection/0.5"
        or not isinstance(source, dict)
        or source.get("experiment") != "relational-contract-discovery-005"
        or not isinstance(gate, dict)
        or gate
        != {"verified": True, "policy_authority": "NONE", "promotion_authorized": False}
        or not isinstance(claim, dict)
        or claim.get("scientific_verdict") != "CAUSAL_UTILITY_PARITY"
        or claim.get("effect")
        != "UNIQUE_CAUSAL_UTILITY_FALSIFIED_WITHIN_TOURNAMENT"
    ):
        raise ValueError("projection claim or authority boundary failed")
    manifest = verify_manifest(verified.path.parent / str(source["manifest"]))
    if source.get("manifest_sha256") != manifest.digest:
        raise ValueError("projection manifest binding failed")
    if source.get("results_sha256") != manifest.document["results"]["sha256"]:
        raise ValueError("projection results binding failed")
    return verified

