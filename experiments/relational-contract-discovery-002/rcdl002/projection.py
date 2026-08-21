"""Fail-closed RCDL-002 projection for Receipt Gate and Claim Graph."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rcdl.canonical import canonical_json, load_json_bytes

PROJECTION_SCHEMA = "openline.ace.relational-contract-projection/0.2"


class ProjectionVerificationError(ValueError):
    pass


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


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
            "standing": "LOCAL_DETERMINISTIC_TRANSPORT_ONLY",
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
                        "held_out_new_tasks": item["held_out"][
                            "same_implementation_new_tasks"
                        ],
                    },
                }
                for item in supported
            ],
        },
        "contract_families": manifest["minimal_contract_families"],
        "transport": {
            "cross_domain_frozen_engine": manifest["transport"][
                "cross_domain_frozen_engine"
            ],
            "independent_implementation": manifest["transport"][
                "independent_implementation"
            ],
        },
        "recovery": dict(manifest["recovery"]),
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
        raise ProjectionVerificationError("unsupported projection schema")
    if payload != canonical_json(document) + b"\n":
        raise ProjectionVerificationError("projection bytes are not canonical")
    if set(document) != {
        "schema",
        "source",
        "authority",
        "receipt_gate",
        "claim_graph",
        "contract_families",
        "transport",
        "recovery",
    }:
        raise ProjectionVerificationError("projection top-level closure failed")
    authority = document["authority"]
    gate = document["receipt_gate"]
    graph = document["claim_graph"]
    if (
        not isinstance(authority, dict)
        or set(authority)
        != {"ace_level", "authorization", "receiver_must_reverify", "reason"}
        or authority.get("authorization") != "NONE"
        or authority.get("ace_level") != "1_CANDIDATE"
        or authority.get("receiver_must_reverify") is not True
        or not isinstance(authority.get("reason"), str)
        or not authority["reason"]
    ):
        raise ProjectionVerificationError("projection authority boundary failed")
    if gate != {
        "eligible_as_policy_input": False,
        "eligible_as_evidence_attachment": True,
    }:
        raise ProjectionVerificationError("projection receipt-gate boundary failed")
    if (
        not isinstance(graph, dict)
        or set(graph) != {"standing", "claims"}
        or graph.get("standing") != "LOCAL_DETERMINISTIC_TRANSPORT_ONLY"
    ):
        raise ProjectionVerificationError("projection Claim Graph standing is invalid")
    claims = graph.get("claims")
    if not isinstance(claims, list) or len(claims) != 4 or not all(
        isinstance(item, dict)
        and set(item) == {"claim_id", "clause_digest", "standing", "evidence"}
        and item.get("standing") == "SUPPORTED"
        and isinstance(item.get("claim_id"), str)
        and _is_sha256(item.get("clause_digest"))
        and isinstance(item.get("evidence"), dict)
        and set(item["evidence"])
        == {
            "active_oracle_failure_rate_ppm",
            "sham_oracle_failure_rate_ppm",
            "held_out_new_tasks",
        }
        and item["evidence"]["active_oracle_failure_rate_ppm"] == 1_000_000
        and item["evidence"]["sham_oracle_failure_rate_ppm"] == 0
        and item["evidence"]["held_out_new_tasks"] is True
        for item in claims
    ):
        raise ProjectionVerificationError("projection claims are invalid")
    from .workflow import TARGET_CLAUSE_IDS, workflow_candidate_clauses

    frozen = {clause.id: clause.digest for clause in workflow_candidate_clauses()}
    if (
        {item["claim_id"] for item in claims} != TARGET_CLAUSE_IDS
        or any(item["clause_digest"] != frozen[item["claim_id"]] for item in claims)
        or document["contract_families"] != [sorted(TARGET_CLAUSE_IDS)]
    ):
        raise ProjectionVerificationError("projection clause source binding failed")
    if document["transport"] != {
        "cross_domain_frozen_engine": True,
        "independent_implementation": "NOT_TESTED",
    }:
        raise ProjectionVerificationError("projection transport boundary failed")
    recovery = document["recovery"]
    if recovery != {
        "status": "SUPPORTED_LOCAL_BOUNDED_PROGRESS",
        "clause_id": "workflow.recovery_requires_fresh_observation",
        "horizon_steps": 3,
        "fairness_assumption": "recovery_available",
    }:
        raise ProjectionVerificationError("projection recovery standing is invalid")
    source = document["source"]
    digest_value = source.get("manifest_sha256") if isinstance(source, dict) else None
    if (
        not isinstance(source, dict)
        or set(source) != {"experiment", "calibration_id", "manifest_sha256"}
        or source.get("experiment") != "relational-contract-discovery-002"
        or not _is_sha256(source.get("calibration_id"))
        or not _is_sha256(digest_value)
    ):
        raise ProjectionVerificationError("projection manifest digest is invalid")
    digest = hashlib.sha256(payload).hexdigest()
    sidecar = target.with_suffix(target.suffix + ".sha256")
    parts = sidecar.read_text(encoding="utf-8").strip().split() if sidecar.is_file() else []
    if len(parts) != 2 or parts[0] != digest or parts[1] != target.name:
        raise ProjectionVerificationError("projection digest sidecar mismatch")
    return ProjectionVerification(digest, len(claims), "NONE")
