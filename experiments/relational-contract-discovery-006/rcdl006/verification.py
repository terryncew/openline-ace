"""Fail-closed verification for RCDL-006 manifests and projections."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import canonical_json, load_json_bytes
from .tournament import (
    CLAIM_EFFECT,
    MANIFEST_SCHEMA,
    PROJECTION_SCHEMA,
    RESULT_SCHEMA,
    SCIENTIFIC_VERDICT,
)


@dataclass(frozen=True)
class VerifiedDocument:
    path: Path
    digest: str
    document: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"path": str(self.path), "sha256": self.digest, "verified": True}


def _bound(path: Path) -> VerifiedDocument:
    payload = path.read_bytes()
    document = load_json_bytes(payload)
    if not isinstance(document, dict) or payload != canonical_json(document) + b"\n":
        raise ValueError(f"non-canonical document: {path.name}")
    digest = hashlib.sha256(payload).hexdigest()
    sidecar = path.with_suffix(path.suffix + ".sha256")
    parts = sidecar.read_text(encoding="utf-8").strip().split() if sidecar.is_file() else []
    if len(parts) != 2 or parts != [digest, path.name]:
        raise ValueError(f"digest sidecar mismatch: {path.name}")
    return VerifiedDocument(path, digest, document)


def verify_manifest(path: str | Path) -> VerifiedDocument:
    verified = _bound(Path(path))
    document = verified.document
    if set(document) != {
        "ace", "claim_effect", "experiment_id", "limitations", "results",
        "schema", "tool_version", "tournament", "verdict",
    }:
        raise ValueError("manifest closure failed")
    if (
        document["schema"] != MANIFEST_SCHEMA
        or document["experiment_id"] != "relational-contract-discovery-006"
        or document["claim_effect"] != CLAIM_EFFECT
        or document["ace"] != {
            "level": "1_CANDIDATE",
            "promotion_authorized": False,
            "receipt_gate_authorization": "NONE",
        }
    ):
        raise ValueError("manifest authority boundary failed")
    tournament = document["tournament"]
    if (
        not isinstance(tournament, dict)
        or tournament.get("protocol_status") != "VALID_RESULT"
        or tournament.get("scientific_verdict") != SCIENTIFIC_VERDICT
        or tournament.get("queries_per_case") != 3
        or tournament.get("heldout_mechanism_compositions") != 6
        or tournament.get("heldout_tasks") != 16
        or tournament.get("matched_sham_failures") != 0
        or tournament.get("energy_mismatches") != 0
        or tournament.get("transport_across_agents") is not True
        or tournament.get("accuracy_delta_ppm") != 0
        or tournament.get("upstream", {}).get("verified") is not True
    ):
        raise ValueError("manifest scientific boundary failed")
    results = document["results"]
    if not isinstance(results, dict) or results != {
        "path": "heldout-mechanism-results.jsonl",
        "row_count": 384,
        "schema": RESULT_SCHEMA,
        "sha256": results.get("sha256"),
    }:
        raise ValueError("manifest results closure failed")
    results_path = verified.path.parent / results["path"]
    payload = results_path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != results["sha256"]:
        raise ValueError("result payload digest mismatch")
    lines = payload.splitlines()
    if len(lines) != 384:
        raise ValueError("result row count mismatch")
    policies: dict[str, int] = {}
    for line in lines:
        record = load_json_bytes(line)
        if not isinstance(record, dict) or line != canonical_json(record):
            raise ValueError("non-canonical result record")
        if (
            record.get("schema") != RESULT_SCHEMA
            or record.get("split") != "evaluation"
            or record.get("correct_standing") is not True
            or record.get("correct_recovery_horizon") is not True
            or record.get("query_transcript", {}).get("query_count") != 3
        ):
            raise ValueError("result record boundary failed")
        policy = str(record.get("policy"))
        policies[policy] = policies.get(policy, 0) + 1
    if policies != {"learned-signature-baseline": 192, "symbolic-rcdl": 192}:
        raise ValueError("policy result balance failed")
    return verified


def verify_projection(path: str | Path) -> VerifiedDocument:
    verified = _bound(Path(path))
    document = verified.document
    if set(document) != {"claim", "gate", "projection_id", "reopen_if", "schema", "source"}:
        raise ValueError("projection closure failed")
    if (
        document["schema"] != PROJECTION_SCHEMA
        or document["projection_id"] != "rcdl-006-envharness-heldout-mechanism"
        or document["gate"] != {
            "policy_authority": "NONE",
            "promotion_authorized": False,
            "verified": True,
        }
        or document["claim"].get("effect") != CLAIM_EFFECT
        or document["claim"].get("scientific_verdict") != SCIENTIFIC_VERDICT
    ):
        raise ValueError("projection authority or claim boundary failed")
    source = document["source"]
    if source.get("experiment") != "relational-contract-discovery-006":
        raise ValueError("projection source failed")
    manifest = verify_manifest(verified.path.parent / source["manifest"])
    if source.get("manifest_sha256") != manifest.digest:
        raise ValueError("projection manifest binding failed")
    if source.get("results_sha256") != manifest.document["results"]["sha256"]:
        raise ValueError("projection results binding failed")
    return verified
