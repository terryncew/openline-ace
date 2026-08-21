"""Fail-closed downstream projection for Receipt Gate and Claim Graph."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import canonical_json, load_json_bytes

PROJECTION_SCHEMA = "openline.ace.relational-contract-projection/0.1"


class ProjectionVerificationError(ValueError):
    pass


@dataclass(frozen=True)
class ProjectionVerification:
    digest: str
    claim_count: int
    authorization: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": True,
            "digest": self.digest,
            "claim_count": self.claim_count,
            "authorization": self.authorization,
        }


def build_projection(manifest: dict[str, Any], manifest_digest: str) -> dict[str, Any]:
    supported = [item for item in manifest["clauses"] if item["standing"] == "SUPPORTED"]
    return {
        "schema": PROJECTION_SCHEMA,
        "source": {
            "experiment": manifest["ace"]["experiment"],
            "calibration_id": manifest["calibration_id"],
            "manifest_sha256": manifest_digest,
        },
        "authority": {
            "ace_level": manifest["ace"]["level"],
            "authorization": "NONE",
            "receiver_must_reverify": True,
            "reason": manifest["ace"]["promotion_blocker"],
        },
        "receipt_gate": {
            "eligible_as_policy_input": False,
            "eligible_as_evidence_attachment": True,
        },
        "claim_graph": {
            "standing": "LOCAL_CALIBRATION_ONLY",
            "claims": [
                {
                    "claim_id": item["id"],
                    "clause_digest": item["digest"],
                    "standing": item["standing"],
                    "evidence": {
                        "active_oracle_failure_rate_ppm": item["intervention"][
                            "active_oracle_failure_rate_ppm"
                        ],
                        "sham_oracle_failure_rate_ppm": item["intervention"][
                            "sham_oracle_failure_rate_ppm"
                        ],
                        "held_out_same_implementation": item["held_out"][
                            "same_implementation_new_seeds"
                        ],
                    },
                }
                for item in supported
            ],
        },
        "contract_families": manifest["minimal_contract_families"],
    }


def write_projection(document: dict[str, Any], path: str | Path) -> str:
    target = Path(path)
    payload = canonical_json(document) + b"\n"
    target.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    target.with_suffix(target.suffix + ".sha256").write_text(
        f"{digest}  {target.name}\n", encoding="utf-8"
    )
    return digest


def verify_projection(path: str | Path) -> ProjectionVerification:
    target = Path(path)
    payload = target.read_bytes()
    document = load_json_bytes(payload)
    if not isinstance(document, dict) or document.get("schema") != PROJECTION_SCHEMA:
        raise ProjectionVerificationError("unsupported projection")
    if payload != canonical_json(document) + b"\n":
        raise ProjectionVerificationError("projection bytes are not canonical")
    if set(document) != {
        "schema",
        "source",
        "authority",
        "receipt_gate",
        "claim_graph",
        "contract_families",
    }:
        raise ProjectionVerificationError("projection top-level closure failed")
    source = document.get("source")
    authority = document.get("authority")
    receipt_gate = document.get("receipt_gate")
    claim_graph = document.get("claim_graph")
    if not all(isinstance(item, dict) for item in (source, authority, receipt_gate, claim_graph)):
        raise ProjectionVerificationError("projection section has an invalid shape")
    manifest_digest = source.get("manifest_sha256")
    if (
        not isinstance(manifest_digest, str)
        or len(manifest_digest) != 64
        or any(character not in "0123456789abcdef" for character in manifest_digest)
    ):
        raise ProjectionVerificationError("projection source digest is invalid")
    if authority.get("authorization") != "NONE":
        raise ProjectionVerificationError("calibration projection must fail closed")
    if (
        authority.get("ace_level") != "1_CANDIDATE"
        or authority.get("receiver_must_reverify") is not True
    ):
        raise ProjectionVerificationError("projection authority boundary is invalid")
    if receipt_gate.get("eligible_as_policy_input") is not False:
        raise ProjectionVerificationError("projection attempts to authorize policy use")
    if receipt_gate.get("eligible_as_evidence_attachment") is not True:
        raise ProjectionVerificationError("projection cannot serve as an evidence attachment")
    if claim_graph.get("standing") != "LOCAL_CALIBRATION_ONLY":
        raise ProjectionVerificationError("projection overstates Claim Graph standing")
    claims = claim_graph.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ProjectionVerificationError("claim projection is missing")
    if not all(
        isinstance(item, dict)
        and item.get("standing") == "SUPPORTED"
        and isinstance(item.get("claim_id"), str)
        and isinstance(item.get("clause_digest"), str)
        for item in claims
    ):
        raise ProjectionVerificationError("projected claim is invalid")
    digest = hashlib.sha256(payload).hexdigest()
    sidecar = target.with_suffix(target.suffix + ".sha256")
    parts = sidecar.read_text(encoding="utf-8").strip().split() if sidecar.is_file() else []
    if len(parts) != 2 or parts[0] != digest or parts[1] != target.name:
        raise ProjectionVerificationError("projection digest sidecar mismatch")
    return ProjectionVerification(digest, len(claims), "NONE")
