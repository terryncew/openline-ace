"""Canonical RCDL-003 manifest writer and fail-closed verifier."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rcdl.canonical import canonical_json, load_json_bytes

from .bindings import verify_frozen_bindings
from .contracts import SPURIOUS_CONTROL_IDS, TARGET_CLAUSE_IDS, clauses_by_id

MANIFEST_SCHEMA = "rcdl.contract-manifest/0.3"
SCIENTIFIC_VERDICTS = {
    "REPLICATION_PASS_RCDL_STRICT_WIN",
    "REPLICATION_PASS_BASELINE_PARITY",
    "REPLICATION_PASS_RCDL_NOT_BEST",
    "REPLICATION_FAIL",
}


class ManifestVerificationError(ValueError):
    pass


@dataclass(frozen=True)
class ManifestVerification:
    digest: str
    verdict: str
    clause_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": True,
            "digest": self.digest,
            "verdict": self.verdict,
            "clause_count": self.clause_count,
            "promotion_authorized": False,
        }


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def write_bound_json(document: dict[str, Any], path: str | Path) -> str:
    target = Path(path)
    payload = canonical_json(document) + b"\n"
    target.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    target.with_suffix(target.suffix + ".sha256").write_text(
        f"{digest}  {target.name}\n", encoding="utf-8"
    )
    return digest


def _verify_sidecar(target: Path, payload: bytes) -> str:
    digest = hashlib.sha256(payload).hexdigest()
    sidecar = target.with_suffix(target.suffix + ".sha256")
    parts = sidecar.read_text(encoding="utf-8").strip().split() if sidecar.is_file() else []
    if len(parts) != 2 or parts[0] != digest or parts[1] != target.name:
        raise ManifestVerificationError("manifest digest sidecar mismatch")
    return digest


def _verify_score(score: Any) -> None:
    fields = {
        "true_positive",
        "true_negative",
        "false_positive",
        "false_negative",
        "accuracy_ppm",
        "balanced_accuracy_ppm",
        "failure_f1_ppm",
    }
    if not isinstance(score, dict) or set(score) != fields:
        raise ManifestVerificationError("classification score closure failed")
    tp, tn, fp, fn = (score[name] for name in (
        "true_positive", "true_negative", "false_positive", "false_negative"
    ))
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (tp, tn, fp, fn)):
        raise ManifestVerificationError("classification counts are invalid")
    total = tp + tn + fp + fn
    positives = tp + fn
    negatives = tn + fp
    if not total or not positives or not negatives:
        raise ManifestVerificationError("classification score lacks both classes")
    accuracy = (tp + tn) * 1_000_000 // total
    balanced = ((tp * 1_000_000 // positives) + (tn * 1_000_000 // negatives)) // 2
    denominator = 2 * tp + fp + fn
    f1 = 0 if not denominator else 2 * tp * 1_000_000 // denominator
    if (score["accuracy_ppm"], score["balanced_accuracy_ppm"], score["failure_f1_ppm"]) != (accuracy, balanced, f1):
        raise ManifestVerificationError("classification metrics do not match counts")


def verify_manifest(path: str | Path) -> ManifestVerification:
    target = Path(path)
    payload = target.read_bytes()
    document = load_json_bytes(payload)
    if not isinstance(document, dict) or document.get("schema") != MANIFEST_SCHEMA:
        raise ManifestVerificationError("unsupported manifest schema")
    if payload != canonical_json(document) + b"\n":
        raise ManifestVerificationError("manifest is not canonical JSON")
    if set(document) != {
        "schema",
        "tool_version",
        "experiment_id",
        "replication_id",
        "ace",
        "source_bindings",
        "implementation_boundary",
        "substrate",
        "clauses",
        "minimal_contract_families",
        "baseline_tournament",
        "transport",
        "recovery",
        "limitations",
        "verdict",
    }:
        raise ManifestVerificationError("manifest top-level closure failed")
    verdict = document["verdict"]
    if verdict not in SCIENTIFIC_VERDICTS or not _is_sha256(document["replication_id"]):
        raise ManifestVerificationError("manifest verdict or identifier is invalid")
    ace = document["ace"]
    if (
        not isinstance(ace, dict)
        or ace.get("level") != "1_CANDIDATE"
        or ace.get("promotion_authorized") is not False
        or not isinstance(ace.get("promotion_blocker"), str)
        or not ace["promotion_blocker"]
    ):
        raise ManifestVerificationError("manifest ACE boundary failed")

    binding = verify_frozen_bindings().to_dict()
    if document["source_bindings"] != binding:
        raise ManifestVerificationError("manifest source bindings are stale")
    boundary = document["implementation_boundary"]
    if boundary != {
        "code_path_independent": True,
        "no_rcdl002_runtime_imports": True,
        "same_repository": True,
        "independent_developer_or_lab": False,
        "external_replication": False,
    }:
        raise ManifestVerificationError("implementation-independence claim expanded")

    clauses = document["clauses"]
    frozen = clauses_by_id()
    if not isinstance(clauses, list) or {item.get("id") for item in clauses if isinstance(item, dict)} != set(frozen):
        raise ManifestVerificationError("manifest clause set differs from frozen contract")
    trials_seen: set[int] = set()
    for item in clauses:
        if not isinstance(item, dict) or set(item) != {
            "id",
            "digest",
            "hook",
            "role",
            "standing",
            "standing_reason",
            "baseline_support",
            "intervention",
            "held_out",
            "nuisance_invariance",
        }:
            raise ManifestVerificationError("manifest clause closure failed")
        clause = frozen[item["id"]]
        if item["digest"] != clause.digest or item["hook"] != clause.hook:
            raise ManifestVerificationError("manifest clause binding failed")
        intervention = item["intervention"]
        if not isinstance(intervention, dict) or set(intervention) != {
            "trials_per_arm",
            "active_oracle_failures",
            "active_clause_failures",
            "sham_oracle_failures",
            "sham_clause_failures",
            "active_oracle_failure_rate_ppm",
            "sham_oracle_failure_rate_ppm",
            "event_count_matched",
            "mutation_energy",
            "active_runs",
            "sham_runs",
        }:
            raise ManifestVerificationError("manifest intervention closure failed")
        trials = intervention["trials_per_arm"]
        if isinstance(trials, bool) or not isinstance(trials, int) or not 2 <= trials <= 64:
            raise ManifestVerificationError("manifest intervention trial count is invalid")
        trials_seen.add(trials)
        for key in ("active_oracle_failures", "active_clause_failures", "sham_oracle_failures", "sham_clause_failures"):
            if isinstance(intervention[key], bool) or not isinstance(intervention[key], int) or not 0 <= intervention[key] <= trials:
                raise ManifestVerificationError("manifest intervention count is invalid")
        if intervention["active_oracle_failure_rate_ppm"] != intervention["active_oracle_failures"] * 1_000_000 // trials:
            raise ManifestVerificationError("active intervention rate mismatch")
        if intervention["sham_oracle_failure_rate_ppm"] != intervention["sham_oracle_failures"] * 1_000_000 // trials:
            raise ManifestVerificationError("sham intervention rate mismatch")
        if intervention["event_count_matched"] is not True or intervention["mutation_energy"] != 1:
            raise ManifestVerificationError("active/sham energy boundary failed")
        if len(intervention["active_runs"]) != trials or len(intervention["sham_runs"]) != trials:
            raise ManifestVerificationError("manifest intervention records are incomplete")
        if not isinstance(item["nuisance_invariance"], dict) or not all(item["nuisance_invariance"].values()):
            raise ManifestVerificationError("manifest nuisance invariance failed")
        if item["held_out"].get("expected_result_replicated") is not True:
            raise ManifestVerificationError("held-out replication did not reproduce")
    if len(trials_seen) != 1:
        raise ManifestVerificationError("manifest uses inconsistent trial counts")

    targets = [item for item in clauses if item["id"] in TARGET_CLAUSE_IDS]
    controls = [item for item in clauses if item["id"] in SPURIOUS_CONTROL_IDS]
    replication_pass = (
        len(targets) == 4
        and len(controls) == 1
        and all(
            item["standing"] == "SUPPORTED"
            and item["standing_reason"] == "INTERVENTIONALLY_NECESSARY_IN_REPLICA"
            and item["intervention"]["active_oracle_failure_rate_ppm"] == 1_000_000
            and item["intervention"]["sham_oracle_failure_rate_ppm"] == 0
            for item in targets
        )
        and controls[0]["standing"] == "REJECTED"
        and controls[0]["standing_reason"] == "REJECTED_CAUSALLY_IRRELEVANT_IN_REPLICA"
        and controls[0]["intervention"]["active_oracle_failure_rate_ppm"] == 0
        and document["minimal_contract_families"] == [sorted(TARGET_CLAUSE_IDS)]
    )

    tournament = document["baseline_tournament"]
    if not isinstance(tournament, dict) or tournament.get("schema") != "rcdl.baseline-tournament/0.1":
        raise ManifestVerificationError("baseline tournament schema failed")
    rcdl_score = tournament.get("rcdl_contract_predictor", {}).get("score")
    _verify_score(rcdl_score)
    baselines = tournament.get("ordinary_baselines")
    if not isinstance(baselines, list) or len(baselines) < 4:
        raise ManifestVerificationError("baseline tournament is incomplete")
    for item in baselines:
        if not isinstance(item, dict) or "score" not in item:
            raise ManifestVerificationError("baseline record is invalid")
        _verify_score(item["score"])
    observed_best = max(
        baselines,
        key=lambda item: (
            item["score"]["balanced_accuracy_ppm"],
            item["score"]["failure_f1_ppm"],
            item["score"]["accuracy_ppm"],
            item["name"],
        ),
    )
    if (
        tournament.get("best_ordinary_baseline") != observed_best["name"]
        or tournament.get("best_ordinary_score") != observed_best["score"]
    ):
        raise ManifestVerificationError("best baseline selection mismatch")
    strict_win = (
        rcdl_score["balanced_accuracy_ppm"]
        > observed_best["score"]["balanced_accuracy_ppm"]
        and rcdl_score["failure_f1_ppm"]
        >= observed_best["score"]["failure_f1_ppm"]
    )
    expected_tournament = (
        "RCDL_STRICT_WIN"
        if strict_win
        else "RCDL_PARITY"
        if rcdl_score["balanced_accuracy_ppm"] == observed_best["score"]["balanced_accuracy_ppm"]
        and rcdl_score["failure_f1_ppm"] == observed_best["score"]["failure_f1_ppm"]
        else "RCDL_NOT_BEST"
    )
    if tournament.get("verdict") != expected_tournament:
        raise ManifestVerificationError("baseline tournament verdict mismatch")
    expected_verdict = (
        "REPLICATION_FAIL"
        if not replication_pass
        else "REPLICATION_PASS_RCDL_STRICT_WIN"
        if expected_tournament == "RCDL_STRICT_WIN"
        else "REPLICATION_PASS_BASELINE_PARITY"
        if expected_tournament == "RCDL_PARITY"
        else "REPLICATION_PASS_RCDL_NOT_BEST"
    )
    if verdict != expected_verdict:
        raise ManifestVerificationError("scientific verdict does not follow evidence")
    if document["transport"] != {
        "frozen_engine": True,
        "frozen_clauses": True,
        "independent_code_path": True,
        "independent_developer_or_lab": False,
        "stochastic_llm_workflow": "NOT_TESTED",
    }:
        raise ManifestVerificationError("transport boundary is invalid")
    digest = _verify_sidecar(target, payload)
    return ManifestVerification(digest, verdict, len(clauses))
