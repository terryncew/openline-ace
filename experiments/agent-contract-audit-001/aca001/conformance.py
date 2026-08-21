from __future__ import annotations

import hashlib
import random
from typing import Any

from .model import ArmResult, AuditPolicy
from .audit import grade_audit


def fixture_candidates() -> list[dict[str, Any]]:
    source = {
        "type": "fixture-proposer",
        "id": "aca001-conformance",
        "authority": "NONE",
    }
    return [
        {
            "candidate_id": "validated-artifact-binding",
            "text": "execute_patch must consume the validated artifact ID produced for the current patch",
            "scope": "conformance/coding-workflow",
            "source": source,
            "relation": {
                "kind": "provenance_freshness",
                "atoms": ["validated_artifact_id(current_patch)->execute_patch"],
                "from": "run_linter",
                "to": "execute_patch",
            },
            "interventions": {
                "active": {"op": "replace_validated_artifact_id", "target": "execute_patch", "parameters": {"with": "prior"}},
                "sham": {"op": "mutate_unrelated_audit_marker", "target": "audit_marker", "parameters": {"size_bucket": "matched"}},
                "restoration": {"op": "restore_validated_artifact_id", "target": "execute_patch", "parameters": {"with": "current"}},
            },
        },
        {
            "candidate_id": "format-scratchpad-ritual",
            "text": "format_scratchpad must run before dispatch",
            "scope": "conformance/coding-workflow",
            "source": source,
            "relation": {
                "kind": "ordering",
                "atoms": ["format_scratchpad<dispatch"],
                "before": "format_scratchpad",
                "after": "dispatch",
            },
            "interventions": {
                "active": {"op": "skip_format_scratchpad", "target": "format_scratchpad", "parameters": {"token_bucket": "matched"}},
                "sham": {"op": "replace_format_scratchpad_with_noop", "target": "format_scratchpad", "parameters": {"token_bucket": "matched"}},
                "restoration": {"op": "restore_format_scratchpad", "target": "format_scratchpad", "parameters": {}},
            },
        },
        {
            "candidate_id": "generic-context-disturbance",
            "text": "a particular context block is causally necessary",
            "scope": "conformance/coding-workflow",
            "source": source,
            "relation": {
                "kind": "context_presence",
                "atoms": ["context_block_present"],
                "subject": "context_block",
            },
            "interventions": {
                "active": {"op": "remove_context_block", "target": "context_block", "parameters": {"token_bucket": "large"}},
                "sham": {"op": "replace_unrelated_block_equal_tokens", "target": "other_context_block", "parameters": {"token_bucket": "large"}},
                "restoration": {"op": "restore_context_block", "target": "context_block", "parameters": {}},
            },
        },
        {
            "candidate_id": "wrapper-audit-marker-rule",
            "text": "the original task requires an audit marker before dispatch",
            "scope": "conformance/coding-workflow",
            "source": source,
            "relation": {
                "kind": "ordering",
                "atoms": ["audit_marker<dispatch"],
                "before": "audit_marker",
                "after": "dispatch",
            },
            "interventions": {
                "active": {"op": "wrapper_block_without_marker", "target": "wrapper", "parameters": {"marker": "audit"}},
                "sham": {"op": "wrapper_noop_same_hook", "target": "wrapper", "parameters": {"marker": "audit"}},
                "restoration": {"op": "restore_marker", "target": "wrapper", "parameters": {"marker": "audit"}},
            },
        },
    ]


def _rng(candidate_id: str, pair_index: int) -> random.Random:
    digest = hashlib.sha256(f"{candidate_id}:{pair_index}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def observational_trace_rows(count: int = 192) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(count):
        digest = hashlib.sha256(f"observational:{index}".encode()).digest()
        rng = random.Random(int.from_bytes(digest[:8], "big"))
        success = rng.random() >= 0.04
        # Both candidate relations are deliberately present on every observed
        # run. They therefore have identical prevalence among successful traces.
        rows.append({
            "run_id": f"obs-{index:04d}",
            "task_id": f"fixture-task-{index % 12:02d}",
            "verifier_success": success,
            "validated_artifact_binding_present": True,
            "format_scratchpad_present": True,
            "audit_marker_present": True,
        })
    return rows


def observational_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [row for row in rows if row["verifier_success"]]
    if not successful:
        raise RuntimeError("observational fixture has no successful runs")
    return {
        "runs": len(rows),
        "successful_runs": len(successful),
        "validated_artifact_binding_prevalence_among_success": (
            sum(bool(r["validated_artifact_binding_present"]) for r in successful) / len(successful)
        ),
        "format_scratchpad_prevalence_among_success": (
            sum(bool(r["format_scratchpad_present"]) for r in successful) / len(successful)
        ),
        "audit_marker_prevalence_among_success": (
            sum(bool(r["audit_marker_present"]) for r in successful) / len(successful)
        ),
    }


def _success(candidate_id: str, arm: str, pair_index: int) -> tuple[bool, str]:
    rng = _rng(candidate_id, pair_index)
    base_good = rng.random() >= 0.03

    if candidate_id == "validated-artifact-binding":
        if arm == "active":
            return (rng.random() >= 0.96, "ok")
        return (base_good, "ok")

    if candidate_id == "format-scratchpad-ritual":
        return (base_good, "ok")

    if candidate_id == "generic-context-disturbance":
        if arm in {"active", "sham"}:
            return (rng.random() >= 0.72, "ok")
        return (base_good, "ok")

    if candidate_id == "wrapper-audit-marker-rule":
        if arm == "active":
            return (base_good, "wrapper_blocked")
        return (base_good, "ok")

    raise KeyError(candidate_id)


def build_fixture_results(pairs_per_candidate: int = 96) -> list[ArmResult]:
    rows: list[ArmResult] = []
    for candidate in fixture_candidates():
        candidate_id = candidate["candidate_id"]
        for index in range(pairs_per_candidate):
            pair_id = f"{candidate_id}:pair-{index:03d}"
            task_id = f"fixture-task-{index % 12:02d}"
            seed = index + 1000
            for arm in ("baseline", "active", "sham", "restoration"):
                success, runner_status = _success(candidate_id, arm, index)
                rows.append(ArmResult(
                    candidate_id=candidate_id,
                    pair_id=pair_id,
                    task_id=task_id,
                    seed=seed,
                    arm=arm,
                    verifier_id="fixture-original-verifier-v1",
                    verifier_success=success,
                    runner_status=runner_status,
                ))
    return rows


def run_conformance(
    pairs_per_candidate: int = 96,
    policy: AuditPolicy | None = None,
) -> dict[str, Any]:
    policy = policy or AuditPolicy()
    candidates = fixture_candidates()
    results = build_fixture_results(pairs_per_candidate)
    audit = grade_audit(candidates, results, policy)
    standings = {g["candidate_id"]: g["standing"] for g in audit["grades"]}
    expected = {
        "validated-artifact-binding": "SUPPORTED",
        "format-scratchpad-ritual": "REJECTED_RITUAL",
        "generic-context-disturbance": "UNDECIDABLE_SHAM_EFFECT",
        "wrapper-audit-marker-rule": "REJECTED_RITUAL",
    }
    obs_rows = observational_trace_rows()
    obs_summary = observational_summary(obs_rows)
    observational_pair_equal = (
        obs_summary["validated_artifact_binding_prevalence_among_success"]
        == obs_summary["format_scratchpad_prevalence_among_success"]
        == 1.0
    )
    verdict = (
        "CONFORMANCE_PASS_EXTERNAL_UNRUN"
        if standings == expected and observational_pair_equal
        else "CONFORMANCE_FAIL"
    )
    return {
        "verdict": verdict,
        "scientific_standing": "MECHANICS_ONLY_NOT_EXTERNAL_AGENT_EVIDENCE",
        "authority": "NONE",
        "pairs_per_candidate": pairs_per_candidate,
        "candidates": candidates,
        "rows": [r.as_dict() for r in results],
        "audit": audit,
        "expected_standings": expected,
        "observed_standings": standings,
        "observational_rows": obs_rows,
        "observational_summary": obs_summary,
        "blind_external_lane": "UNRUN",
    }
