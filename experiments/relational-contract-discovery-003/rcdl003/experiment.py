"""Closed-loop RCDL-003 independent-code-path replication."""

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

from . import __version__
from .bindings import verify_frozen_bindings
from .contracts import (
    SPURIOUS_CONTROL_IDS,
    TARGET_CLAUSE_IDS,
    clauses_by_id,
    frozen_clauses,
)
from .manifest import MANIFEST_SCHEMA, write_bound_json
from .oracle import check_external_behavior
from .projection import build_projection, write_projection
from .replica import ALL_HOOKS, RECOVERY_HORIZON, LedgerRun, run_batch, run_pair
from .tournament import run_tournament


def _prepare_output(path: Path, force: bool) -> None:
    if path.exists() and any(path.iterdir()):
        if not force:
            raise FileExistsError(f"output directory is not empty: {path}")
        for child in path.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    path.mkdir(parents=True, exist_ok=True)


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


def _trial_record(clause, run: LedgerRun) -> dict[str, Any]:
    evaluation = evaluate(clause, run.trace)
    oracle = check_external_behavior(run.outcome)
    return {
        "run_id": run.trace.run_id,
        "trace_digest": canonical_digest(run.trace.to_dict()),
        "event_count": len(run.trace.events),
        "clause_passed": evaluation.passed,
        "clause_violation_count": evaluation.violation_count,
        "oracle_passed": oracle.passed,
        "failed_properties": sorted(name for name, value in oracle.properties.items() if not value),
    }


def _nuisance_ok(clause, run: LedgerRun) -> dict[str, bool]:
    original = evaluate(clause, run.trace)
    variants = nuisance_variants(run.trace)
    otlp = trace_from_otlp(trace_to_otlp(run.trace))
    return {
        "actor_renaming": _same_evaluation(original, evaluate(clause, variants[0])),
        "event_id_renumbering": _same_evaluation(original, evaluate(clause, variants[1])),
        "object_key_reordering": _same_evaluation(original, evaluate(clause, variants[2])),
        "otel_round_trip": _same_evaluation(original, evaluate(clause, otlp)),
    }


def run_experiment(
    output: str | Path,
    *,
    trials: int = 8,
    force: bool = False,
) -> dict[str, Any]:
    if isinstance(trials, bool) or not isinstance(trials, int) or not 2 <= trials <= 64:
        raise ValueError("trials must be an integer in [2, 64]")
    output_path = Path(output)
    _prepare_output(output_path, force)
    traces_path = output_path / "representative-traces"
    traces_path.mkdir()
    binding = verify_frozen_bindings()
    candidates = frozen_clauses()
    by_id = clauses_by_id()
    training_seeds = tuple(range(trials))
    held_out_seeds = tuple(10_000 + value for value in range(trials))
    baseline_runs = tuple(
        run_pair(clause.hook, "sham", seed)
        for seed in training_seeds
        for clause in candidates
    )
    if not all(check_external_behavior(run.outcome).passed for run in baseline_runs):
        raise RuntimeError("replica produced a failed sham baseline")
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
        nuisance = {
            "actor_renaming": True,
            "event_id_renumbering": True,
            "object_key_reordering": True,
            "otel_round_trip": True,
        }
        event_count_matched = True
        for seed in training_seeds:
            active = run_pair(clause.hook, "active", seed)
            sham = run_pair(clause.hook, "sham", seed)
            active_records.append(_trial_record(clause, active))
            sham_records.append(_trial_record(clause, sham))
            event_count_matched = event_count_matched and len(active.trace.events) == len(sham.trace.events)
            for run in (active, sham):
                observed = _nuisance_ok(clause, run)
                nuisance = {key: nuisance[key] and observed[key] for key in nuisance}
            if seed == training_seeds[0]:
                active.trace.write(traces_path / f"{clause.id}.active.json")
                sham.trace.write(traces_path / f"{clause.id}.sham.json")
        for seed in held_out_seeds:
            active = _trial_record(clause, run_pair(clause.hook, "active", seed))
            sham = _trial_record(clause, run_pair(clause.hook, "sham", seed))
            held_out_records.append({"seed": seed, "active": active, "sham": sham})

        active_oracle = sum(not item["oracle_passed"] for item in active_records)
        active_clause = sum(not item["clause_passed"] for item in active_records)
        sham_oracle = sum(not item["oracle_passed"] for item in sham_records)
        sham_clause = sum(not item["clause_passed"] for item in sham_records)
        target_result = all(
            not item["active"]["oracle_passed"]
            and not item["active"]["clause_passed"]
            and item["sham"]["oracle_passed"]
            and item["sham"]["clause_passed"]
            for item in held_out_records
        )
        control_result = all(
            item["active"]["oracle_passed"]
            and not item["active"]["clause_passed"]
            and item["sham"]["oracle_passed"]
            and item["sham"]["clause_passed"]
            for item in held_out_records
        )
        mined = mining_by_id[clause.id]
        if clause.id in TARGET_CLAUSE_IDS:
            role = "frozen_target_clause"
            supported = (
                mined.accepted
                and active_oracle == trials
                and active_clause == trials
                and sham_oracle == 0
                and sham_clause == 0
                and event_count_matched
                and all(nuisance.values())
                and target_result
            )
            standing_reason = (
                "INTERVENTIONALLY_NECESSARY_IN_REPLICA"
                if supported
                else "REPLICATION_FAILURE"
            )
            expected = target_result
        elif clause.id in SPURIOUS_CONTROL_IDS:
            role = "frozen_spurious_control"
            supported = False
            expected = control_result
            standing_reason = (
                "REJECTED_CAUSALLY_IRRELEVANT_IN_REPLICA"
                if mined.accepted
                and active_clause == trials
                and active_oracle == 0
                and sham_oracle == 0
                and sham_clause == 0
                and event_count_matched
                and all(nuisance.values())
                and control_result
                else "REPLICATION_FAILURE"
            )
        else:
            raise RuntimeError("unclassified frozen clause")
        clause_records.append(
            {
                "id": clause.id,
                "digest": clause.digest,
                "hook": clause.hook,
                "role": role,
                "standing": "SUPPORTED" if supported else "REJECTED",
                "standing_reason": standing_reason,
                "baseline_support": mined.to_dict(),
                "intervention": {
                    "trials_per_arm": trials,
                    "active_oracle_failures": active_oracle,
                    "active_clause_failures": active_clause,
                    "sham_oracle_failures": sham_oracle,
                    "sham_clause_failures": sham_clause,
                    "active_oracle_failure_rate_ppm": active_oracle * 1_000_000 // trials,
                    "sham_oracle_failure_rate_ppm": sham_oracle * 1_000_000 // trials,
                    "event_count_matched": event_count_matched,
                    "mutation_energy": 1,
                    "active_runs": active_records,
                    "sham_runs": sham_records,
                },
                "held_out": {
                    "independent_code_path_new_seeds": True,
                    "expected_result_replicated": expected,
                    "runs": held_out_records,
                },
                "nuisance_invariance": nuisance,
            }
        )

    supported_ids = {
        item["id"] for item in clause_records if item["standing"] == "SUPPORTED"
    }
    family_seeds = tuple(20_000 + value for value in range(trials))
    family_cache: dict[tuple[str, ...], bool] = {}

    def family_passes(family: frozenset[str]) -> bool:
        key = tuple(sorted(family))
        if key in family_cache:
            return family_cache[key]
        enabled_hooks = {by_id[item].hook for item in family}
        passed = all(
            check_external_behavior(
                run_batch(
                    (by_id[target].hook,),
                    active_hooks=()
                    if by_id[target].hook in enabled_hooks
                    else (by_id[target].hook,),
                    seed=seed,
                ).outcome
            ).passed
            for target in TARGET_CLAUSE_IDS
            for seed in family_seeds
        )
        family_cache[key] = passed
        return passed

    families = inclusion_minimal_families(supported_ids, family_passes)
    controls_rejected = all(
        item["standing_reason"] == "REJECTED_CAUSALLY_IRRELEVANT_IN_REPLICA"
        for item in clause_records
        if item["id"] in SPURIOUS_CONTROL_IDS
    )
    replication_pass = (
        supported_ids == TARGET_CLAUSE_IDS
        and controls_rejected
        and families == (TARGET_CLAUSE_IDS,)
    )
    tournament = run_tournament(
        adapted_training_seeds=training_seeds,
        held_out_seeds=tuple(30_000 + value for value in range(trials)),
    )
    if not replication_pass:
        verdict = "REPLICATION_FAIL"
    elif tournament["verdict"] == "RCDL_STRICT_WIN":
        verdict = "REPLICATION_PASS_RCDL_STRICT_WIN"
    elif tournament["verdict"] == "RCDL_PARITY":
        verdict = "REPLICATION_PASS_BASELINE_PARITY"
    else:
        verdict = "REPLICATION_PASS_RCDL_NOT_BEST"
    parameters = {
        "tool_version": __version__,
        "trials": trials,
        "training_seeds": list(training_seeds),
        "held_out_seeds": list(held_out_seeds),
        "family_seeds": list(family_seeds),
        "clause_digests": [clause.digest for clause in candidates],
        "engine_aggregate_sha256": binding.engine_aggregate_sha256,
        "source_implementation_sha256": binding.source_implementation_sha256,
        "replica_implementation_sha256": binding.replica_implementation_sha256,
    }
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "tool_version": __version__,
        "experiment_id": "relational-contract-discovery-003",
        "replication_id": canonical_digest(parameters),
        "ace": {
            "level": "1_CANDIDATE",
            "promotion_authorized": False,
            "promotion_blocker": (
                "Same repository and builder; no independent lab, strong learned baseline, "
                "or stochastic LLM transport."
            ),
        },
        "source_bindings": binding.to_dict(),
        "implementation_boundary": {
            "code_path_independent": True,
            "no_rcdl002_runtime_imports": True,
            "same_repository": True,
            "independent_developer_or_lab": False,
            "external_replication": False,
        },
        "substrate": {
            "name": "deterministic_queue_driven_repair_ledger",
            "roles": ["dispatcher", "builder", "validator", "signoff", "publisher"],
            "multi_fault_batches": True,
            "learned_models": False,
            "external_oracle_separate_from_trace": True,
            "intervention_labels_in_trace": False,
        },
        "clauses": clause_records,
        "minimal_contract_families": [sorted(family) for family in families],
        "baseline_tournament": tournament,
        "transport": {
            "frozen_engine": True,
            "frozen_clauses": True,
            "independent_code_path": True,
            "independent_developer_or_lab": False,
            "stochastic_llm_workflow": "NOT_TESTED",
        },
        "recovery": {
            "status": "SUPPORTED_IN_DETERMINISTIC_REPLICA",
            "clause_id": "workflow.recovery_requires_fresh_observation",
            "horizon_steps": RECOVERY_HORIZON,
            "fairness_assumption": "recovery_available",
        },
        "limitations": [
            "Code-path independence is not independent-team or external replication.",
            "The clause vocabulary and actuators remain domain supplied.",
            "The tournament uses bounded dependency-free baselines, not strong learned sequence or graph models.",
            "Deterministic seeds are not independent stochastic samples; no significance claim is made.",
            "Structural event-count matching is not token, wall-clock timing, or semantic-shock matching.",
            "No stochastic or learned agents are tested.",
            "The evidence projection grants no policy authority.",
        ],
        "verdict": verdict,
    }
    manifest_path = output_path / "contract-manifest.json"
    manifest_digest = write_bound_json(manifest, manifest_path)
    projection_path = output_path / "contract-projection.json"
    projection_digest = write_projection(
        build_projection(manifest, manifest_digest), projection_path
    )
    summary = {
        "schema": "rcdl.replication-summary/0.3",
        "verdict": verdict,
        "manifest": manifest_path.name,
        "manifest_digest": manifest_digest,
        "projection": projection_path.name,
        "projection_digest": projection_digest,
        "candidate_clause_count": len(candidates),
        "supported_clause_count": len(supported_ids),
        "spurious_control_rejected_count": int(controls_rejected),
        "minimal_family_count": len(families),
        "trials_per_arm": trials,
        "baseline_verdict": tournament["verdict"],
        "best_ordinary_baseline": tournament["best_ordinary_baseline"],
        "code_path_independent": True,
        "external_replication": False,
    }
    (output_path / "summary.json").write_bytes(canonical_json(summary) + b"\n")
    return summary
