"""Closed-loop active intervention calibration over the Raft substrate."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from . import __version__
from .canonical import canonical_digest, canonical_json
from .evaluator import Evaluation, evaluate
from .manifest import MANIFEST_SCHEMA, write_manifest
from .miner import filter_candidates
from .nuisance import nuisance_variants
from .oracle import check_raft_safety
from .projection import build_projection, write_projection
from .raft import (
    ALL_HOOKS,
    HOOK_SCENARIOS,
    SAFETY_CLAUSE_IDS,
    SPURIOUS_CONTROL_IDS,
    raft_candidate_clauses,
    run_intervention,
    run_scenario,
)
from .reference import load_reference_record, verify_reference
from .reducer import inclusion_minimal_families
from .trace import Trace

SAFETY_PROPERTIES = (
    "election_safety",
    "leader_completeness",
    "log_matching",
    "state_machine_safety",
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


def _trial_record(clause, trace: Trace) -> dict[str, Any]:
    evaluation = evaluate(clause, trace)
    oracle = check_raft_safety(trace)
    return {
        "run_id": trace.run_id,
        "trace_digest": canonical_digest(trace.to_dict()),
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


def run_calibration(output: str | Path, *, trials: int = 8, force: bool = False) -> dict[str, Any]:
    if isinstance(trials, bool) or not isinstance(trials, int) or not 2 <= trials <= 64:
        raise ValueError("trials must be an integer in [2, 64]")
    output_path = Path(output)
    _prepare_output(output_path, force)
    reference_record = load_reference_record()
    reference_verification = verify_reference()
    traces_path = output_path / "representative-traces"
    traces_path.mkdir()

    candidates = raft_candidate_clauses()
    training_seeds = tuple(range(trials))
    held_out_seeds = tuple(10_000 + seed for seed in range(trials))
    baseline_traces: list[Trace] = []
    for seed in training_seeds:
        baseline_traces.append(run_scenario("healthy", seed))
        for scenario in sorted(set(HOOK_SCENARIOS.values())):
            baseline_traces.append(run_scenario(scenario, seed))
    if not all(check_raft_safety(trace).passed for trace in baseline_traces):
        raise RuntimeError("calibration substrate produced an unsafe baseline")

    mining = filter_candidates(
        candidates,
        tuple(baseline_traces),
        min_support=max(2, trials),
    )
    mining_by_id = {item.clause.id: item for item in mining}
    clause_records: list[dict[str, Any]] = []

    for clause in candidates:
        active_records: list[dict[str, Any]] = []
        sham_records: list[dict[str, Any]] = []
        held_out_records: list[dict[str, Any]] = []
        nuisance_ok = True

        for seed in training_seeds:
            active = run_intervention(clause.hook, "active", seed)
            sham = run_intervention(clause.hook, "sham", seed)
            active_records.append(_trial_record(clause, active))
            sham_records.append(_trial_record(clause, sham))
            if seed == training_seeds[0]:
                active.write(traces_path / f"{clause.id}.active.json")
                sham.write(traces_path / f"{clause.id}.sham.json")
            for source in (active, sham):
                original = evaluate(clause, source)
                if not all(
                    _same_evaluation(original, evaluate(clause, variant))
                    for variant in nuisance_variants(source)
                ):
                    nuisance_ok = False

        for seed in held_out_seeds:
            active = _trial_record(clause, run_intervention(clause.hook, "active", seed))
            sham = _trial_record(clause, run_intervention(clause.hook, "sham", seed))
            held_out_records.append({"seed": seed, "active": active, "sham": sham})

        active_oracle_failures = sum(not item["oracle_passed"] for item in active_records)
        active_clause_failures = sum(not item["clause_passed"] for item in active_records)
        sham_oracle_failures = sum(not item["oracle_passed"] for item in sham_records)
        sham_clause_failures = sum(not item["clause_passed"] for item in sham_records)
        held_out_ok = all(
            not item["active"]["oracle_passed"]
            and not item["active"]["clause_passed"]
            and item["sham"]["oracle_passed"]
            and item["sham"]["clause_passed"]
            for item in held_out_records
        )
        held_out_spurious_rejection = all(
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
            and held_out_ok
        )
        if clause.id in SAFETY_CLAUSE_IDS:
            calibration_role = "known_safety_target"
            expected_outcome_replicated = held_out_ok
        elif clause.id in SPURIOUS_CONTROL_IDS:
            calibration_role = "spurious_observational_control"
            expected_outcome_replicated = held_out_spurious_rejection
        else:  # pragma: no cover - the frozen calibration catalogue is closed.
            raise RuntimeError(f"candidate has no calibration role: {clause.id}")
        if supported:
            standing_reason = "INTERVENTIONALLY_NECESSARY"
        elif (
            mined.accepted
            and active_clause_failures == trials
            and active_oracle_failures == 0
            and sham_oracle_failures == 0
            and sham_clause_failures == 0
            and nuisance_ok
            and held_out_spurious_rejection
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
                    "active_oracle_failure_rate_ppm": active_oracle_failures * 1_000_000 // trials,
                    "active_clause_failure_rate_ppm": active_clause_failures * 1_000_000 // trials,
                    "sham_oracle_failure_rate_ppm": sham_oracle_failures * 1_000_000 // trials,
                    "sham_clause_failure_rate_ppm": sham_clause_failures * 1_000_000 // trials,
                    "effect_delta_ppm": (active_oracle_failures - sham_oracle_failures)
                    * 1_000_000
                    // trials,
                    "energy_matched": True,
                    "active_runs": active_records,
                    "sham_runs": sham_records,
                },
                "nuisance_invariance": {
                    "node_renaming": nuisance_ok,
                    "event_id_renumbering": nuisance_ok,
                    "object_key_reordering": nuisance_ok,
                },
                "held_out": {
                    "same_implementation_new_seeds": held_out_ok,
                    "spurious_control_rejection": held_out_spurious_rejection,
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
        cache_key = tuple(sorted(family))
        if cache_key in family_cache:
            return family_cache[cache_key]
        enabled = frozenset(clause_by_id[item].hook for item in family)
        safe = True
        for seed in family_seeds:
            for scenario in sorted(set(HOOK_SCENARIOS.values())):
                trace = run_scenario(
                    scenario,
                    seed,
                    enabled_hooks=enabled,
                    arm="family",
                )
                if not check_raft_safety(trace).passed:
                    safe = False
                    break
            if not safe:
                break
        family_cache[cache_key] = safe
        return safe

    families = inclusion_minimal_families(supported_ids, family_passes)
    rejected_ids = {
        record["id"] for record in clause_records if record["standing"] == "REJECTED"
    }
    expected_targets_supported = supported_ids == SAFETY_CLAUSE_IDS
    expected_controls_rejected = rejected_ids == SPURIOUS_CONTROL_IDS and all(
        record["standing_reason"] == "REJECTED_CAUSALLY_IRRELEVANT"
        and record["held_out"]["expected_outcome_replicated"]
        for record in clause_records
        if record["id"] in SPURIOUS_CONTROL_IDS
    )
    verdict = (
        "CALIBRATION_PASS"
        if expected_targets_supported and expected_controls_rejected and families
        else "CALIBRATION_FAIL"
    )
    calibration_parameters = {
        "tool_version": __version__,
        "trials": trials,
        "training_seeds": list(training_seeds),
        "held_out_seeds": list(held_out_seeds),
        "candidate_digests": [clause.digest for clause in candidates],
        "raft_reference_sha256": reference_verification.content_sha256,
    }
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "tool_version": __version__,
        "calibration_id": canonical_digest(calibration_parameters),
        "ace": {
            "experiment": "relational-contract-discovery-001",
            "backend_role": "earned_rule_discovery",
            "level": "1_CANDIDATE",
            "promotion_authorized": False,
            "promotion_blocker": "No machine-checked refinement mapping or TLC mutant campaign.",
        },
        "substrate": {
            "name": "deterministic_three_node_raft_micro_harness",
            "oracle_properties": list(SAFETY_PROPERTIES),
            "fault_model": "non_byzantine_targeted_guard_bypass",
            "baseline_trace_count": len(baseline_traces),
        },
        "model_reference": {
            "name": reference_record["name"],
            "repository": reference_record["repository"],
            "commit": reference_record["commit"],
            "content_sha256": reference_verification.content_sha256,
            "git_blob_sha1": reference_verification.git_blob_sha1,
            "record_digest": reference_verification.record_digest,
            "mapped_safety_properties": reference_record["mapped_safety_properties"],
            "execution_binding": reference_verification.execution_binding,
            "tlc_execution": reference_verification.tlc_execution,
        },
        "grammar": {
            "schema": "rcdl.clause/0.1",
            "canonical_representation": "restricted_canonical_json",
            "max_join_fields": 4,
            "max_key_fields": 4,
            "arbitrary_recursion": False,
            "floating_point": False,
            "oracle_predicates_visible_to_miner": False,
        },
        "candidate_mining": {
            "source": "finite_domain_hypothesis_space",
            "open_ended_ilp": False,
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
            "held_out_scenarios_same_implementation": all(
                record["held_out"]["expected_outcome_replicated"]
                for record in clause_records
            ),
            "cross_implementation": "NOT_TESTED",
            "learned_agent_workflows": "OUT_OF_SCOPE",
        },
        "recovery": {
            "status": "NOT_APPLICABLE_PREFIX_CLOSED_SAFETY",
            "reason": "A historical safety violation cannot be undone by later restoration.",
        },
        "limitations": [
            "The candidate vocabulary and actuator map are domain supplied.",
            "Candidate proposal is finite support filtering, not open-ended ILP synthesis.",
            "Minimality is relative to the frozen grammar and perturbation regime.",
            "Held-out transport uses new seeds and node labels, not another Raft implementation.",
            "This calibration makes no claim about stochastic or learned-agent systems.",
            "Bounded observational checks are not formal bisimulation.",
            "The official TLA+ specification is identity-pinned but is not executed by this RC.",
            "The micro-harness has no machine-checked refinement mapping to the official model.",
        ],
        "verdict": verdict,
    }
    manifest_path = output_path / "contract-manifest.json"
    digest = write_manifest(manifest, manifest_path)
    projection_path = output_path / "contract-projection.json"
    projection_digest = write_projection(
        build_projection(manifest, digest), projection_path
    )
    summary = {
        "schema": "rcdl.calibration-summary/0.1",
        "verdict": verdict,
        "manifest": manifest_path.name,
        "manifest_digest": digest,
        "projection": projection_path.name,
        "projection_digest": projection_digest,
        "supported_clause_count": len(supported_ids),
        "rejected_clause_count": len(rejected_ids),
        "spurious_control_rejected_count": len(rejected_ids & SPURIOUS_CONTROL_IDS),
        "candidate_clause_count": len(candidates),
        "minimal_family_count": len(families),
        "trials_per_arm": trials,
    }
    (output_path / "summary.json").write_bytes(canonical_json(summary) + b"\n")
    return summary
