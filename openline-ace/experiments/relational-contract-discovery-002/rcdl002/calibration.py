"""Closed-loop deterministic calibration over the repair-workflow substrate."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from rcdl.canonical import canonical_digest, canonical_json
from rcdl.evaluator import Evaluation, evaluate
from rcdl.miner import filter_candidates
from rcdl.nuisance import nuisance_variants
from rcdl.otel import trace_from_otlp, trace_to_otlp
from rcdl.reducer import inclusion_minimal_families
from rcdl.trace import Trace

from . import __version__
from .engine_reference import verify_engine_reference
from .manifest import MANIFEST_SCHEMA, write_manifest
from .oracle import WorkflowOracleReport, check_workflow_behavior
from .projection import build_projection, write_projection
from .workflow import (
    ALL_HOOKS,
    HOOK_SCENARIOS,
    RECOVERY_HORIZON,
    SPURIOUS_CONTROL_IDS,
    TARGET_CLAUSE_IDS,
    WorkflowRun,
    run_intervention,
    run_scenario,
    workflow_candidate_clauses,
)

ORACLE_PROPERTIES = (
    "correct_release_decision",
    "hidden_tests",
    "authorized_side_effects",
    "evidence_current",
    "approval_safety",
    "bounded_recovery",
)


def _same_evaluation(left: Evaluation, right: Evaluation) -> bool:
    return (
        left.passed,
        left.trigger_count,
        left.support_count,
        left.violation_count,
    ) == (
        right.passed,
        right.trigger_count,
        right.support_count,
        right.violation_count,
    )


def _trial_record(clause, run: WorkflowRun) -> dict[str, Any]:
    evaluation = evaluate(clause, run.trace)
    oracle = check_workflow_behavior(run.outcome)
    return {
        "run_id": run.trace.run_id,
        "trace_digest": canonical_digest(run.trace.to_dict()),
        "clause_passed": evaluation.passed,
        "clause_violation_count": evaluation.violation_count,
        "oracle_passed": oracle.passed,
        "failed_properties": sorted(
            name for name, passed in oracle.properties.items() if not passed
        ),
    }


def _prepare_output(output: Path, force: bool) -> None:
    if output.exists() and any(output.iterdir()):
        if not force:
            raise FileExistsError(f"output directory is not empty: {output}")
        for child in output.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    output.mkdir(parents=True, exist_ok=True)


def _nuisance_ok(clause, run: WorkflowRun) -> tuple[bool, bool]:
    original = evaluate(clause, run.trace)
    transformed_ok = all(
        _same_evaluation(original, evaluate(clause, variant))
        for variant in nuisance_variants(run.trace)
    )
    normalized = trace_from_otlp(trace_to_otlp(run.trace))
    otel_ok = _same_evaluation(original, evaluate(clause, normalized))
    return transformed_ok, otel_ok


def run_calibration(
    output: str | Path,
    *,
    trials: int = 8,
    force: bool = False,
) -> dict[str, Any]:
    if isinstance(trials, bool) or not isinstance(trials, int) or not 2 <= trials <= 64:
        raise ValueError("trials must be an integer in [2, 64]")
    output_path = Path(output)
    _prepare_output(output_path, force)
    engine = verify_engine_reference()
    traces_path = output_path / "representative-traces"
    traces_path.mkdir()

    candidates = workflow_candidate_clauses()
    training_seeds = tuple(range(trials))
    held_out_seeds = tuple(10_000 + seed for seed in range(trials))
    scenarios = tuple(sorted({"healthy", *HOOK_SCENARIOS.values()}))
    baseline_runs = tuple(
        run_scenario(scenario, seed)
        for seed in training_seeds
        for scenario in scenarios
    )
    if not all(check_workflow_behavior(run.outcome).passed for run in baseline_runs):
        raise RuntimeError("workflow substrate produced an invalid successful baseline")
    mining = filter_candidates(
        candidates,
        tuple(run.trace for run in baseline_runs),
        min_support=max(2, trials),
    )
    mining_by_id = {item.clause.id: item for item in mining}
    clause_records: list[dict[str, Any]] = []

    for clause in candidates:
        active_records: list[dict[str, Any]] = []
        sham_records: list[dict[str, Any]] = []
        held_out_records: list[dict[str, Any]] = []
        nuisance_ok = True
        otel_ok = True

        for seed in training_seeds:
            active = run_intervention(clause.hook, "active", seed)
            sham = run_intervention(clause.hook, "sham", seed)
            active_records.append(_trial_record(clause, active))
            sham_records.append(_trial_record(clause, sham))
            if seed == training_seeds[0]:
                active.trace.write(traces_path / f"{clause.id}.active.json")
                sham.trace.write(traces_path / f"{clause.id}.sham.json")
            for run in (active, sham):
                transformed, otel = _nuisance_ok(clause, run)
                nuisance_ok = nuisance_ok and transformed
                otel_ok = otel_ok and otel

        for seed in held_out_seeds:
            active = _trial_record(clause, run_intervention(clause.hook, "active", seed))
            sham = _trial_record(clause, run_intervention(clause.hook, "sham", seed))
            held_out_records.append({"seed": seed, "active": active, "sham": sham})

        active_oracle_failures = sum(not item["oracle_passed"] for item in active_records)
        active_clause_failures = sum(not item["clause_passed"] for item in active_records)
        sham_oracle_failures = sum(not item["oracle_passed"] for item in sham_records)
        sham_clause_failures = sum(not item["clause_passed"] for item in sham_records)
        held_out_target = all(
            not item["active"]["oracle_passed"]
            and not item["active"]["clause_passed"]
            and item["sham"]["oracle_passed"]
            and item["sham"]["clause_passed"]
            for item in held_out_records
        )
        held_out_spurious = all(
            item["active"]["oracle_passed"]
            and not item["active"]["clause_passed"]
            and item["sham"]["oracle_passed"]
            and item["sham"]["clause_passed"]
            for item in held_out_records
        )
        mined = mining_by_id[clause.id]
        supported = (
            mined.accepted
            and active_oracle_failures == trials
            and active_clause_failures == trials
            and sham_oracle_failures == 0
            and sham_clause_failures == 0
            and nuisance_ok
            and otel_ok
            and held_out_target
        )
        if clause.id in TARGET_CLAUSE_IDS:
            calibration_role = "known_workflow_contract_target"
            expected_outcome_replicated = held_out_target
        elif clause.id in SPURIOUS_CONTROL_IDS:
            calibration_role = "spurious_observational_control"
            expected_outcome_replicated = held_out_spurious
        else:
            raise RuntimeError(f"candidate has no frozen calibration role: {clause.id}")
        if supported:
            standing_reason = "INTERVENTIONALLY_NECESSARY"
        elif (
            mined.accepted
            and active_clause_failures == trials
            and active_oracle_failures == 0
            and sham_oracle_failures == 0
            and sham_clause_failures == 0
            and nuisance_ok
            and otel_ok
            and held_out_spurious
        ):
            standing_reason = "REJECTED_CAUSALLY_IRRELEVANT"
        else:
            standing_reason = "REJECTED_CALIBRATION_FAILURE"
        clause_records.append(
            {
                "id": clause.id,
                "digest": clause.digest,
                "kind": clause.kind,
                "hook": clause.hook,
                "calibration_role": calibration_role,
                "standing": "SUPPORTED" if supported else "REJECTED",
                "standing_reason": standing_reason,
                "baseline": mined.to_dict(),
                "intervention": {
                    "trials_per_arm": trials,
                    "active_oracle_failure_rate_ppm": active_oracle_failures
                    * 1_000_000
                    // trials,
                    "active_clause_failure_rate_ppm": active_clause_failures
                    * 1_000_000
                    // trials,
                    "sham_oracle_failure_rate_ppm": sham_oracle_failures
                    * 1_000_000
                    // trials,
                    "sham_clause_failure_rate_ppm": sham_clause_failures
                    * 1_000_000
                    // trials,
                    "effect_delta_ppm": (active_oracle_failures - sham_oracle_failures)
                    * 1_000_000
                    // trials,
                    "energy_matched": True,
                    "active_runs": active_records,
                    "sham_runs": sham_records,
                },
                "nuisance_invariance": {
                    "actor_renaming": nuisance_ok,
                    "event_id_renumbering": nuisance_ok,
                    "object_key_reordering": nuisance_ok,
                    "otel_round_trip": otel_ok,
                },
                "held_out": {
                    "same_implementation_new_tasks": expected_outcome_replicated,
                    "spurious_control_rejection": held_out_spurious,
                    "expected_outcome_replicated": expected_outcome_replicated,
                    "runs": held_out_records,
                },
            }
        )

    supported_ids = {
        record["id"] for record in clause_records if record["standing"] == "SUPPORTED"
    }
    clause_by_id = {clause.id: clause for clause in candidates}
    family_cache: dict[tuple[str, ...], bool] = {}
    family_seeds = tuple(20_000 + seed for seed in range(trials))

    def family_passes(family: frozenset[str]) -> bool:
        key = tuple(sorted(family))
        if key in family_cache:
            return family_cache[key]
        enabled = frozenset(clause_by_id[item].hook for item in family)
        passed = all(
            check_workflow_behavior(
                run_scenario(scenario, seed, enabled_hooks=enabled, arm="family").outcome
            ).passed
            for seed in family_seeds
            for scenario in sorted(set(HOOK_SCENARIOS.values()))
        )
        family_cache[key] = passed
        return passed

    families = inclusion_minimal_families(supported_ids, family_passes)
    rejected_ids = {
        record["id"] for record in clause_records if record["standing"] == "REJECTED"
    }
    targets_supported = supported_ids == TARGET_CLAUSE_IDS
    controls_rejected = rejected_ids == SPURIOUS_CONTROL_IDS and all(
        record["standing_reason"] == "REJECTED_CAUSALLY_IRRELEVANT"
        and record["held_out"]["expected_outcome_replicated"]
        for record in clause_records
        if record["id"] in SPURIOUS_CONTROL_IDS
    )
    verdict = (
        "CALIBRATION_PASS"
        if targets_supported and controls_rejected and families == (TARGET_CLAUSE_IDS,)
        else "CALIBRATION_FAIL"
    )
    parameters = {
        "tool_version": __version__,
        "trials": trials,
        "training_seeds": list(training_seeds),
        "held_out_seeds": list(held_out_seeds),
        "candidate_digests": [clause.digest for clause in candidates],
        "engine_aggregate_sha256": engine.aggregate_sha256,
    }
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "tool_version": __version__,
        "calibration_id": canonical_digest(parameters),
        "ace": {
            "experiment": "relational-contract-discovery-002",
            "backend_role": "deterministic_cross_domain_transport",
            "level": "1_CANDIDATE",
            "promotion_authorized": False,
            "promotion_blocker": "No independent workflow implementation, stochastic LLM transport, or ordinary baseline comparison.",
        },
        "substrate": {
            "name": "deterministic_rule_based_code_repair_workflow",
            "roles": ["planner", "implementer", "tester", "reviewer"],
            "oracle_properties": list(ORACLE_PROPERTIES),
            "fault_model": "targeted_guard_bypass",
            "baseline_trace_count": len(baseline_runs),
            "learned_models": False,
        },
        "engine_reference": engine.to_dict(),
        "grammar": {
            "schema": "rcdl.clause/0.1",
            "source_experiment": "relational-contract-discovery-001",
            "engine_modified": False,
            "open_ended_ilp": False,
            "oracle_predicates_visible_to_miner": False,
        },
        "candidate_mining": {
            "source": "finite_domain_hypothesis_space",
            "actionability_required": True,
            "oracle_labels_visible_to_miner": False,
            "spurious_control_count": len(SPURIOUS_CONTROL_IDS),
            "results": [item.to_dict() for item in mining],
            "family_reduction": {
                "method": "exhaustive_inclusion_minimal_enumeration",
                "candidate_bound": 16,
                "seeds": list(family_seeds),
                "scenario_count": len(set(HOOK_SCENARIOS.values())),
                "evaluated_family_count": len(family_cache),
            },
        },
        "clauses": clause_records,
        "minimal_contract_families": [sorted(family) for family in families],
        "transport": {
            "cross_domain_frozen_engine": True,
            "source_domain": "deterministic_raft",
            "target_domain": "deterministic_code_repair_workflow",
            "held_out_new_tasks_same_implementation": all(
                record["held_out"]["expected_outcome_replicated"]
                for record in clause_records
            ),
            "independent_implementation": "NOT_TESTED",
            "stochastic_llm_workflow": "NOT_TESTED",
        },
        "recovery": {
            "status": "SUPPORTED_LOCAL_BOUNDED_PROGRESS",
            "clause_id": "workflow.recovery_requires_fresh_observation",
            "horizon_steps": RECOVERY_HORIZON,
            "fairness_assumption": "recovery_available",
        },
        "limitations": [
            "The candidate vocabulary and actuator map are domain supplied.",
            "Candidate proposal is finite support filtering, not open-ended ILP synthesis.",
            "The external oracle and workflow implementation were built in the same experiment package.",
            "Task transport uses new deterministic seeds, not an independent implementation.",
            "Structural energy matching does not establish token, timing, or semantic-shock matching.",
            "The experiment contains no stochastic or learned agents.",
            "The projection is evidence-only and grants no policy authority.",
        ],
        "verdict": verdict,
    }
    manifest_path = output_path / "contract-manifest.json"
    manifest_digest = write_manifest(manifest, manifest_path)
    projection_path = output_path / "contract-projection.json"
    projection_digest = write_projection(
        build_projection(manifest, manifest_digest), projection_path
    )
    summary = {
        "schema": "rcdl.calibration-summary/0.2",
        "verdict": verdict,
        "manifest": manifest_path.name,
        "manifest_digest": manifest_digest,
        "projection": projection_path.name,
        "projection_digest": projection_digest,
        "candidate_clause_count": len(candidates),
        "supported_clause_count": len(supported_ids),
        "rejected_clause_count": len(rejected_ids),
        "spurious_control_rejected_count": len(rejected_ids & SPURIOUS_CONTROL_IDS),
        "minimal_family_count": len(families),
        "bounded_recovery_supported_count": sum(
            record["id"] == "workflow.recovery_requires_fresh_observation"
            and record["standing"] == "SUPPORTED"
            for record in clause_records
        ),
        "trials_per_arm": trials,
        "engine_modified": False,
    }
    (output_path / "summary.json").write_bytes(canonical_json(summary) + b"\n")
    return summary
