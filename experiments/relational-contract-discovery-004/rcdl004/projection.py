"""Bounded handoff projection for RCDL-004."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rcdl.canonical import canonical_json, load_json_bytes

PROJECTION_SCHEMA = "openline.ace.relational-contract-projection/0.4"


class ProjectionVerificationError(ValueError):
    pass


@dataclass(frozen=True)
class ProjectionVerification:
    digest: str
    predictive_standing: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": True,
            "digest": self.digest,
            "predictive_standing": self.predictive_standing,
            "receipt_gate_policy_authority": False,
        }


def build_projection(manifest: dict[str, Any], manifest_digest: str) -> dict[str, Any]:
    verdict = manifest["tournament"]["scientific_verdict"]
    standing = (
        "REJECTED_BY_BOUNDED_LEARNED_PARITY"
        if verdict == "LEARNED_PARITY"
        else "REJECTED_BY_BOUNDED_LEARNED_SUPERIORITY"
        if verdict == "LEARNED_STRICT_WIN"
        else "SUPPORTED_AGAINST_DECLARED_LEARNED_BASELINES"
        if verdict == "RCDL_STRICT_WIN"
        else "UNDECIDABLE_MIXED_RESULT"
    )
    return {
        "schema": PROJECTION_SCHEMA,
        "source": {
            "experiment": "relational-contract-discovery-004",
            "manifest_sha256": manifest_digest,
            "pressure_test_id": manifest["pressure_test_id"],
        },
        "claim_graph": {
            "claim": "RCDL has unique predictive advantage over learned relational trace models on this substrate",
            "standing": standing,
            "causal_legibility": "NOT_TESTED_BY_PREDICTIVE_PARITY",
            "interventional_necessity": "CARRIED_FROM_RCDL_003_NOT_REESTABLISHED_HERE",
        },
        "tournament": {
            "scientific_verdict": verdict,
            "best_learned_model": manifest["tournament"]["best_learned_model"],
            "rcdl_score": manifest["tournament"]["rcdl_contract_predictor"]["test_score"],
            "best_learned_score": manifest["tournament"]["best_learned_score"],
        },
        "receipt_gate": {
            "eligible_as_evidence_attachment": True,
            "eligible_as_policy_input": False,
        },
        "authority": {
            "ace_level": "1_CANDIDATE",
            "authorization": "NONE",
            "receiver_must_reverify": True,
        },
        "remaining_falsifiers": [
            "prospective external replication by an independent developer or laboratory",
            "neural sequence or graph models with external tuning",
            "stochastic LLM workflow transport",
            "token timing and semantic-shock matched shams",
            "open-ended clause discovery",
        ],
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
    if not isinstance(document, dict) or payload != canonical_json(document) + b"\n":
        raise ProjectionVerificationError("projection is not canonical")
    digest = hashlib.sha256(payload).hexdigest()
    sidecar = target.with_suffix(target.suffix + ".sha256")
    parts = sidecar.read_text(encoding="utf-8").strip().split() if sidecar.is_file() else []
    if len(parts) != 2 or parts[0] != digest or parts[1] != target.name:
        raise ProjectionVerificationError("projection sidecar mismatch")
    if set(document) != {
        "schema", "source", "claim_graph", "tournament", "receipt_gate", "authority", "remaining_falsifiers"
    } or document["schema"] != PROJECTION_SCHEMA:
        raise ProjectionVerificationError("projection closure failed")
    if document["receipt_gate"] != {
        "eligible_as_evidence_attachment": True,
        "eligible_as_policy_input": False,
    } or document["authority"] != {
        "ace_level": "1_CANDIDATE",
        "authorization": "NONE",
        "receiver_must_reverify": True,
    }:
        raise ProjectionVerificationError("projection authority expanded")
    standing = document["claim_graph"].get("standing")
    allowed = {
        "REJECTED_BY_BOUNDED_LEARNED_PARITY",
        "REJECTED_BY_BOUNDED_LEARNED_SUPERIORITY",
        "SUPPORTED_AGAINST_DECLARED_LEARNED_BASELINES",
        "UNDECIDABLE_MIXED_RESULT",
    }
    if standing not in allowed:
        raise ProjectionVerificationError("projection standing is invalid")
    source = document["source"]
    if source.get("experiment") != "relational-contract-discovery-004" or not isinstance(source.get("manifest_sha256"), str):
        raise ProjectionVerificationError("projection source failed")
    return ProjectionVerification(digest, standing)

