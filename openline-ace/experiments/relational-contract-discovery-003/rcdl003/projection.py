"""Bounded evidence-only handoff from RCDL-003."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rcdl.canonical import canonical_digest, canonical_json, load_json_bytes

from .contracts import TARGET_CLAUSE_IDS, clauses_by_id

PROJECTION_SCHEMA = "openline.ace.relational-contract-projection/0.3"


class ProjectionVerificationError(ValueError):
    pass


@dataclass(frozen=True)
class ProjectionVerification:
    digest: str
    claim_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": True,
            "digest": self.digest,
            "claim_count": self.claim_count,
            "authorization": "NONE",
        }


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def build_projection(manifest: dict[str, Any], manifest_digest: str) -> dict[str, Any]:
    supported = [item for item in manifest["clauses"] if item["standing"] == "SUPPORTED"]
    standing = (
        "DETERMINISTIC_CODE_PATH_REPLICATION_WITH_BOUNDED_BASELINE_WIN"
        if manifest["baseline_tournament"]["verdict"] == "RCDL_STRICT_WIN"
        else "DETERMINISTIC_CODE_PATH_REPLICATION_WITHOUT_BASELINE_WIN"
    )
    return {
        "schema": PROJECTION_SCHEMA,
        "source": {
            "experiment": manifest["experiment_id"],
            "replication_id": manifest["replication_id"],
            "manifest_sha256": manifest_digest,
        },
        "authority": {
            "ace_level": "1_CANDIDATE",
            "authorization": "NONE",
            "receiver_must_reverify": True,
            "reason": manifest["ace"]["promotion_blocker"],
        },
        "receipt_gate": {
            "eligible_as_policy_input": False,
            "eligible_as_evidence_attachment": True,
        },
        "claim_graph": {
            "standing": standing,
            "claims": [
                {
                    "claim_id": item["id"],
                    "clause_digest": item["digest"],
                    "standing": "SUPPORTED_IN_INDEPENDENT_CODE_PATH",
                    "active_oracle_failure_rate_ppm": item["intervention"]["active_oracle_failure_rate_ppm"],
                    "sham_oracle_failure_rate_ppm": item["intervention"]["sham_oracle_failure_rate_ppm"],
                }
                for item in supported
            ],
        },
        "contract_families": manifest["minimal_contract_families"],
        "baseline_tournament": {
            "digest": canonical_digest(manifest["baseline_tournament"]),
            "verdict": manifest["baseline_tournament"]["verdict"],
            "best_ordinary_baseline": manifest["baseline_tournament"]["best_ordinary_baseline"],
        },
        "transport": dict(manifest["transport"]),
        "recovery": dict(manifest["recovery"]),
        "remaining_falsifiers": [
            "independent developer or laboratory replication",
            "strong learned sequence and graph baselines",
            "stochastic LLM workflow transport",
            "token, timing, and semantic-shock matched shams",
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
    if not isinstance(document, dict) or document.get("schema") != PROJECTION_SCHEMA:
        raise ProjectionVerificationError("unsupported projection schema")
    if payload != canonical_json(document) + b"\n":
        raise ProjectionVerificationError("projection is not canonical")
    if set(document) != {
        "schema", "source", "authority", "receipt_gate", "claim_graph",
        "contract_families", "baseline_tournament", "transport", "recovery",
        "remaining_falsifiers",
    }:
        raise ProjectionVerificationError("projection top-level closure failed")
    authority = document["authority"]
    if (
        authority.get("ace_level") != "1_CANDIDATE"
        or authority.get("authorization") != "NONE"
        or authority.get("receiver_must_reverify") is not True
    ):
        raise ProjectionVerificationError("projection authority expanded")
    if document["receipt_gate"] != {
        "eligible_as_policy_input": False,
        "eligible_as_evidence_attachment": True,
    }:
        raise ProjectionVerificationError("projection gate boundary failed")
    graph = document["claim_graph"]
    claims = graph.get("claims") if isinstance(graph, dict) else None
    frozen = clauses_by_id()
    if not isinstance(claims, list) or len(claims) != 4:
        raise ProjectionVerificationError("projection claim count is invalid")
    if {item.get("claim_id") for item in claims} != TARGET_CLAUSE_IDS:
        raise ProjectionVerificationError("projection claim set is invalid")
    for item in claims:
        if (
            item.get("clause_digest") != frozen[item["claim_id"]].digest
            or item.get("standing") != "SUPPORTED_IN_INDEPENDENT_CODE_PATH"
            or item.get("active_oracle_failure_rate_ppm") != 1_000_000
            or item.get("sham_oracle_failure_rate_ppm") != 0
        ):
            raise ProjectionVerificationError("projection claim evidence is invalid")
    if document["contract_families"] != [sorted(TARGET_CLAUSE_IDS)]:
        raise ProjectionVerificationError("projection minimal family is invalid")
    transport = document["transport"]
    if transport.get("independent_code_path") is not True or transport.get("independent_developer_or_lab") is not False or transport.get("stochastic_llm_workflow") != "NOT_TESTED":
        raise ProjectionVerificationError("projection transport claim expanded")
    source = document["source"]
    if (
        source.get("experiment") != "relational-contract-discovery-003"
        or not _is_sha256(source.get("replication_id"))
        or not _is_sha256(source.get("manifest_sha256"))
    ):
        raise ProjectionVerificationError("projection source binding is invalid")
    digest = hashlib.sha256(payload).hexdigest()
    sidecar = target.with_suffix(target.suffix + ".sha256")
    parts = sidecar.read_text(encoding="utf-8").strip().split() if sidecar.is_file() else []
    if len(parts) != 2 or parts[0] != digest or parts[1] != target.name:
        raise ProjectionVerificationError("projection sidecar mismatch")
    return ProjectionVerification(digest, len(claims))
