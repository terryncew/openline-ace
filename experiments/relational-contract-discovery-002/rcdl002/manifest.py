"""RCDL-002 manifest writing and fail-closed verification."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rcdl.canonical import canonical_json, load_json_bytes

MANIFEST_SCHEMA = "rcdl.contract-manifest/0.2"


class ManifestVerificationError(ValueError):
    pass


@dataclass(frozen=True)
class ManifestVerification:
    path: str
    digest: str
    clause_count: int
    verdict: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": True,
            "path": self.path,
            "digest": self.digest,
            "clause_count": self.clause_count,
            "verdict": self.verdict,
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


def _sidecar_digest(target: Path, payload: bytes) -> str:
    digest = hashlib.sha256(payload).hexdigest()
    sidecar = target.with_suffix(target.suffix + ".sha256")
    parts = sidecar.read_text(encoding="utf-8").strip().split() if sidecar.is_file() else []
    if len(parts) != 2 or parts[0] != digest or parts[1] != target.name:
        raise ManifestVerificationError("manifest digest sidecar mismatch")
    return digest


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _verify_trial_record(item: Any) -> None:
    if not isinstance(item, dict) or set(item) != {
        "run_id",
        "trace_digest",
        "clause_passed",
        "clause_violation_count",
        "oracle_passed",
        "failed_properties",
    }:
        raise ManifestVerificationError("manifest trial record is invalid")
    if (
        not isinstance(item["run_id"], str)
        or not item["run_id"]
        or not _is_sha256(item["trace_digest"])
        or not isinstance(item["clause_passed"], bool)
        or isinstance(item["clause_violation_count"], bool)
        or not isinstance(item["clause_violation_count"], int)
        or item["clause_violation_count"] < 0
        or not isinstance(item["oracle_passed"], bool)
        or not isinstance(item["failed_properties"], list)
        or not all(isinstance(value, str) and value for value in item["failed_properties"])
    ):
        raise ManifestVerificationError("manifest trial record values are invalid")


def _failure_rate(records: list[dict[str, Any]], field: str) -> int:
    return sum(not item[field] for item in records) * 1_000_000 // len(records)


def verify_manifest(path: str | Path) -> ManifestVerification:
    target = Path(path)
    payload = target.read_bytes()
    document = load_json_bytes(payload)
    if not isinstance(document, dict) or document.get("schema") != MANIFEST_SCHEMA:
        raise ManifestVerificationError("unsupported manifest schema")
    if payload != canonical_json(document) + b"\n":
        raise ManifestVerificationError("manifest bytes are not canonical")
    expected_top = {
        "schema",
        "tool_version",
        "calibration_id",
        "ace",
        "substrate",
        "engine_reference",
        "grammar",
        "candidate_mining",
        "clauses",
        "minimal_contract_families",
        "transport",
        "recovery",
        "limitations",
        "verdict",
    }
    if set(document) != expected_top:
        raise ManifestVerificationError("manifest top-level closure failed")
    verdict = document["verdict"]
    if verdict not in {"CALIBRATION_PASS", "CALIBRATION_FAIL"}:
        raise ManifestVerificationError("invalid manifest verdict")
    if not _is_sha256(document["calibration_id"]):
        raise ManifestVerificationError("manifest calibration identifier is invalid")
    clauses = document["clauses"]
    if not isinstance(clauses, list) or not clauses:
        raise ManifestVerificationError("manifest has no clauses")
    ids = [item.get("id") for item in clauses if isinstance(item, dict)]
    if len(ids) != len(clauses) or len(set(ids)) != len(ids) or not all(
        isinstance(item, str) and item for item in ids
    ):
        raise ManifestVerificationError("manifest clause identifiers are invalid")
    from .workflow import (  # Local import avoids a module-load cycle.
        SPURIOUS_CONTROL_IDS,
        TARGET_CLAUSE_IDS,
        workflow_candidate_clauses,
    )

    frozen = {clause.id: clause for clause in workflow_candidate_clauses()}
    if set(ids) != set(frozen):
        raise ManifestVerificationError("manifest clause set differs from frozen candidates")
    trials_seen: set[int] = set()
    for item in clauses:
        if set(item) != {
            "id",
            "digest",
            "kind",
            "hook",
            "calibration_role",
            "standing",
            "standing_reason",
            "baseline",
            "intervention",
            "nuisance_invariance",
            "held_out",
        }:
            raise ManifestVerificationError("manifest clause closure failed")
        clause = frozen[item["id"]]
        if (
            item["digest"] != clause.digest
            or item["kind"] != clause.kind
            or item["hook"] != clause.hook
        ):
            raise ManifestVerificationError("manifest clause source binding failed")
        for field in ("baseline", "intervention", "held_out", "nuisance_invariance"):
            if not isinstance(item.get(field), dict):
                raise ManifestVerificationError(f"manifest clause {field} is invalid")
        if set(item["nuisance_invariance"]) != {
            "actor_renaming",
            "event_id_renumbering",
            "object_key_reordering",
            "otel_round_trip",
        }:
            raise ManifestVerificationError("manifest nuisance control set is invalid")
        baseline = item["baseline"]
        if (
            set(baseline)
            != {
                "clause_id",
                "clause_digest",
                "accepted",
                "trigger_count",
                "support_count",
                "violation_count",
                "reason",
            }
            or baseline["clause_id"] != clause.id
            or baseline["clause_digest"] != clause.digest
            or baseline["accepted"] is not True
            or baseline["reason"] != "no_baseline_violations_with_positive_support"
            or baseline["violation_count"] != 0
            or not isinstance(baseline["trigger_count"], int)
            or not isinstance(baseline["support_count"], int)
            or baseline["support_count"] < 2
        ):
            raise ManifestVerificationError("manifest baseline evidence is invalid")
        intervention = item["intervention"]
        if set(intervention) != {
            "trials_per_arm",
            "active_oracle_failure_rate_ppm",
            "active_clause_failure_rate_ppm",
            "sham_oracle_failure_rate_ppm",
            "sham_clause_failure_rate_ppm",
            "effect_delta_ppm",
            "energy_matched",
            "active_runs",
            "sham_runs",
        }:
            raise ManifestVerificationError("manifest intervention closure failed")
        trials = intervention["trials_per_arm"]
        active_runs = intervention["active_runs"]
        sham_runs = intervention["sham_runs"]
        if (
            isinstance(trials, bool)
            or not isinstance(trials, int)
            or not 2 <= trials <= 64
            or not isinstance(active_runs, list)
            or not isinstance(sham_runs, list)
            or len(active_runs) != trials
            or len(sham_runs) != trials
            or intervention["energy_matched"] is not True
        ):
            raise ManifestVerificationError("manifest intervention trials are invalid")
        for record in [*active_runs, *sham_runs]:
            _verify_trial_record(record)
        expected_rates = {
            "active_oracle_failure_rate_ppm": _failure_rate(
                active_runs, "oracle_passed"
            ),
            "active_clause_failure_rate_ppm": _failure_rate(
                active_runs, "clause_passed"
            ),
            "sham_oracle_failure_rate_ppm": _failure_rate(sham_runs, "oracle_passed"),
            "sham_clause_failure_rate_ppm": _failure_rate(sham_runs, "clause_passed"),
        }
        if any(intervention[field] != value for field, value in expected_rates.items()):
            raise ManifestVerificationError("manifest intervention rate mismatch")
        if intervention["effect_delta_ppm"] != (
            expected_rates["active_oracle_failure_rate_ppm"]
            - expected_rates["sham_oracle_failure_rate_ppm"]
        ):
            raise ManifestVerificationError("manifest intervention effect mismatch")
        trials_seen.add(trials)
        held_out = item["held_out"]
        if set(held_out) != {
            "same_implementation_new_tasks",
            "spurious_control_rejection",
            "expected_outcome_replicated",
            "runs",
        } or not isinstance(held_out["runs"], list):
            raise ManifestVerificationError("manifest held-out closure failed")
        if len(held_out["runs"]) != trials:
            raise ManifestVerificationError("manifest held-out trial count mismatch")
        for record in held_out["runs"]:
            if not isinstance(record, dict) or set(record) != {"seed", "active", "sham"}:
                raise ManifestVerificationError("manifest held-out record is invalid")
            if isinstance(record["seed"], bool) or not isinstance(record["seed"], int):
                raise ManifestVerificationError("manifest held-out seed is invalid")
            _verify_trial_record(record["active"])
            _verify_trial_record(record["sham"])
    if len(trials_seen) != 1:
        raise ManifestVerificationError("manifest uses inconsistent trial counts")

    mining = document["candidate_mining"]
    if (
        not isinstance(mining, dict)
        or mining.get("source") != "finite_domain_hypothesis_space"
        or mining.get("actionability_required") is not True
        or mining.get("oracle_labels_visible_to_miner") is not False
        or mining.get("spurious_control_count") != 1
        or not isinstance(mining.get("results"), list)
        or not all(isinstance(item, dict) for item in mining["results"])
        or {item.get("clause_id") for item in mining["results"]} != set(frozen)
    ):
        raise ManifestVerificationError("manifest candidate-mining boundary failed")
    for item in mining["results"]:
        clause = frozen[item["clause_id"]]
        if item.get("clause_digest") != clause.digest or item.get("accepted") is not True:
            raise ManifestVerificationError("manifest candidate-mining binding failed")

    grammar = document["grammar"]
    if grammar != {
        "schema": "rcdl.clause/0.1",
        "source_experiment": "relational-contract-discovery-001",
        "engine_modified": False,
        "open_ended_ilp": False,
        "oracle_predicates_visible_to_miner": False,
    }:
        raise ManifestVerificationError("manifest grammar boundary failed")

    if verdict == "CALIBRATION_PASS":
        targets = [
            item
            for item in clauses
            if item.get("calibration_role") == "known_workflow_contract_target"
        ]
        controls = [
            item
            for item in clauses
            if item.get("calibration_role") == "spurious_observational_control"
        ]
        if (
            len(targets) != 4
            or len(controls) != 1
            or len(clauses) != 5
            or {item["id"] for item in targets} != TARGET_CLAUSE_IDS
            or {item["id"] for item in controls} != SPURIOUS_CONTROL_IDS
        ):
            raise ManifestVerificationError("pass verdict has an invalid role set")
        if not all(
            item.get("standing") == "SUPPORTED"
            and item.get("standing_reason") == "INTERVENTIONALLY_NECESSARY"
            and item["baseline"].get("accepted") is True
            and item["intervention"].get("active_oracle_failure_rate_ppm") == 1_000_000
            and item["intervention"].get("active_clause_failure_rate_ppm") == 1_000_000
            and item["intervention"].get("sham_oracle_failure_rate_ppm") == 0
            and item["intervention"].get("sham_clause_failure_rate_ppm") == 0
            and item["held_out"].get("expected_outcome_replicated") is True
            and item["held_out"].get("same_implementation_new_tasks") is True
            and all(item["nuisance_invariance"].values())
            for item in targets
        ):
            raise ManifestVerificationError("pass verdict contains an unsupported target")
        control = controls[0]
        if not (
            control.get("standing") == "REJECTED"
            and control.get("standing_reason") == "REJECTED_CAUSALLY_IRRELEVANT"
            and control["baseline"].get("accepted") is True
            and control["intervention"].get("active_oracle_failure_rate_ppm") == 0
            and control["intervention"].get("active_clause_failure_rate_ppm") == 1_000_000
            and control["intervention"].get("sham_oracle_failure_rate_ppm") == 0
            and control["intervention"].get("sham_clause_failure_rate_ppm") == 0
            and control["held_out"].get("expected_outcome_replicated") is True
            and control["held_out"].get("spurious_control_rejection") is True
            and all(control["nuisance_invariance"].values())
        ):
            raise ManifestVerificationError("spurious control was not causally rejected")
        supported_ids = {item["id"] for item in targets}
        families = document["minimal_contract_families"]
        if families != [sorted(supported_ids)]:
            raise ManifestVerificationError("minimal contract family is not the frozen target family")
        ace = document["ace"]
        if (
            not isinstance(ace, dict)
            or ace.get("level") != "1_CANDIDATE"
            or ace.get("promotion_authorized") is not False
        ):
            raise ManifestVerificationError("manifest attempts unauthorized promotion")
        engine = document["engine_reference"]
        if not isinstance(engine, dict) or engine.get("engine_modified") is not False:
            raise ManifestVerificationError("frozen engine boundary failed")
        transport = document["transport"]
        if (
            not isinstance(transport, dict)
            or transport.get("cross_domain_frozen_engine") is not True
            or transport.get("independent_implementation") != "NOT_TESTED"
            or transport.get("stochastic_llm_workflow") != "NOT_TESTED"
        ):
            raise ManifestVerificationError("transport boundary is invalid")
        recovery = document["recovery"]
        if (
            not isinstance(recovery, dict)
            or recovery.get("status") != "SUPPORTED_LOCAL_BOUNDED_PROGRESS"
            or recovery.get("horizon_steps") != 3
        ):
            raise ManifestVerificationError("bounded recovery evidence is invalid")

    digest = _sidecar_digest(target, payload)
    return ManifestVerification(str(target), digest, len(clauses), verdict)
