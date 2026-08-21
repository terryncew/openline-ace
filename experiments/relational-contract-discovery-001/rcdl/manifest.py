"""Contract manifest writing and exact-byte verification."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import canonical_json, load_json_bytes

MANIFEST_SCHEMA = "rcdl.contract-manifest/0.1"


class ManifestVerificationError(ValueError):
    """Raised when a manifest or its evidence binding is invalid."""


@dataclass(frozen=True)
class ManifestVerification:
    path: str
    digest: str
    clause_count: int
    verdict: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "digest": self.digest,
            "clause_count": self.clause_count,
            "verdict": self.verdict,
            "verified": True,
        }


def write_manifest(document: dict[str, Any], path: str | Path) -> str:
    target = Path(path)
    payload = canonical_json(document) + b"\n"
    target.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    target.with_suffix(target.suffix + ".sha256").write_text(
        f"{digest}  {target.name}\n", encoding="utf-8"
    )
    return digest


def verify_manifest(path: str | Path) -> ManifestVerification:
    target = Path(path)
    payload = target.read_bytes()
    document = load_json_bytes(payload)
    if not isinstance(document, dict):
        raise ManifestVerificationError("manifest must be an object")
    canonical_payload = canonical_json(document) + b"\n"
    if payload != canonical_payload:
        raise ManifestVerificationError("manifest bytes are not canonical")
    if document.get("schema") != MANIFEST_SCHEMA:
        raise ManifestVerificationError("unsupported manifest schema")
    if set(document) != {
        "schema",
        "tool_version",
        "calibration_id",
        "ace",
        "substrate",
        "model_reference",
        "grammar",
        "candidate_mining",
        "clauses",
        "minimal_contract_families",
        "transport",
        "recovery",
        "limitations",
        "verdict",
    }:
        raise ManifestVerificationError("manifest top-level closure failed")
    clauses = document["clauses"]
    if not isinstance(clauses, list) or not clauses:
        raise ManifestVerificationError("manifest has no clauses")
    verdict = document["verdict"]
    if verdict not in {"CALIBRATION_PASS", "CALIBRATION_FAIL"}:
        raise ManifestVerificationError("invalid verdict")
    if not all(isinstance(item, dict) for item in clauses):
        raise ManifestVerificationError("manifest clause record must be an object")
    for item in clauses:
        for field in ("baseline", "intervention", "held_out", "nuisance_invariance"):
            if not isinstance(item.get(field), dict):
                raise ManifestVerificationError(f"manifest clause {field} record is invalid")
        if set(item["nuisance_invariance"]) != {
            "node_renaming",
            "event_id_renumbering",
            "object_key_reordering",
        }:
            raise ManifestVerificationError("manifest nuisance control set is invalid")
    clause_ids = [item.get("id") for item in clauses]
    if not all(isinstance(item, str) and item for item in clause_ids):
        raise ManifestVerificationError("manifest clause identifier is invalid")
    if len(set(clause_ids)) != len(clause_ids):
        raise ManifestVerificationError("manifest clause identifiers are not unique")
    if verdict == "CALIBRATION_PASS":
        targets = [
            item for item in clauses if item.get("calibration_role") == "known_safety_target"
        ]
        controls = [
            item
            for item in clauses
            if item.get("calibration_role") == "spurious_observational_control"
        ]
        if len(targets) + len(controls) != len(clauses) or not targets or not controls:
            raise ManifestVerificationError("pass verdict has an invalid calibration role set")
        if not all(
            item.get("standing") == "SUPPORTED"
            and item.get("standing_reason") == "INTERVENTIONALLY_NECESSARY"
            and item.get("baseline", {}).get("accepted") is True
            and item.get("intervention", {}).get("active_oracle_failure_rate_ppm")
            == 1_000_000
            and item.get("intervention", {}).get("active_clause_failure_rate_ppm")
            == 1_000_000
            and item.get("intervention", {}).get("sham_oracle_failure_rate_ppm") == 0
            and item.get("intervention", {}).get("sham_clause_failure_rate_ppm") == 0
            and item.get("held_out", {}).get("expected_outcome_replicated") is True
            and all(item.get("nuisance_invariance", {}).values())
            for item in targets
        ):
            raise ManifestVerificationError("pass verdict contains an unsupported safety target")
        if not all(
            item.get("standing") == "REJECTED"
            and item.get("standing_reason") == "REJECTED_CAUSALLY_IRRELEVANT"
            and item.get("baseline", {}).get("accepted") is True
            and item.get("intervention", {}).get("active_oracle_failure_rate_ppm") == 0
            and item.get("intervention", {}).get("active_clause_failure_rate_ppm")
            == 1_000_000
            and item.get("intervention", {}).get("sham_oracle_failure_rate_ppm") == 0
            and item.get("intervention", {}).get("sham_clause_failure_rate_ppm") == 0
            and item.get("held_out", {}).get("expected_outcome_replicated") is True
            and all(item.get("nuisance_invariance", {}).values())
            for item in controls
        ):
            raise ManifestVerificationError("spurious observational control was not rejected")
        families = document["minimal_contract_families"]
        if not isinstance(families, list) or not families:
            raise ManifestVerificationError("pass verdict has no minimal family")
        supported_ids = {item["id"] for item in targets}
        for family in families:
            if (
                not isinstance(family, list)
                or not family
                or not all(isinstance(item, str) for item in family)
                or len(set(family)) != len(family)
                or not set(family) <= supported_ids
            ):
                raise ManifestVerificationError("minimal family references invalid clauses")
        ace = document["ace"]
        if not isinstance(ace, dict):
            raise ManifestVerificationError("manifest ACE boundary is invalid")
        if ace.get("promotion_authorized") is not False or ace.get("level") != "1_CANDIDATE":
            raise ManifestVerificationError("calibration cannot authorize ACE promotion")
        reference = document["model_reference"]
        if not isinstance(reference, dict):
            raise ManifestVerificationError("manifest model reference is invalid")
        if (
            reference.get("execution_binding") != "PROPERTY_MAPPING_ONLY"
            or reference.get("tlc_execution") != "NOT_RUN"
        ):
            raise ManifestVerificationError("reference execution boundary mismatch")

    digest = hashlib.sha256(payload).hexdigest()
    sidecar = target.with_suffix(target.suffix + ".sha256")
    if not sidecar.is_file():
        raise ManifestVerificationError("digest sidecar is missing")
    parts = sidecar.read_text(encoding="utf-8").strip().split()
    if len(parts) != 2 or parts[0] != digest or parts[1] != target.name:
        raise ManifestVerificationError("digest sidecar mismatch")
    return ManifestVerification(str(target), digest, len(clauses), verdict)
