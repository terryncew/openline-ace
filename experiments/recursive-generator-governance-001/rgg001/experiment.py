from __future__ import annotations

import hashlib
import json
import math
import secrets
from dataclasses import asdict
from pathlib import Path
from statistics import mean

from .canonical import ReceiptChain, canonical_sha256, sha256_file
from .classifier import CumulativeDriftAuditor, classify_mutation
from .evaluator import ExternalEvaluator, RotatingMetaEvaluator, TaskEvaluator, positive_control
from .generator import initial_generator, proposal_signature, propose_dimension_update, sample_pool
from .model import DIMENSIONS, MutationProposal


def _load_prereg(root: Path) -> dict:
    return json.loads((root / "PREREGISTRATION.json").read_text(encoding="utf-8"))


def _distribution_signature(state) -> dict[str, float]:
    # Coarse behavior-level projection used by cumulative drift audit. It does
    # not trust mutation labels; it observes the generator's emitted cache mode.
    return {str(k): float(v) for k, v in state.cache_key.items()}


def _task_best(task: TaskEvaluator, pool):
    scored = [(task.evaluate(c), c) for c in pool]
    scored.sort(key=lambda pair: (pair[0].score, pair[0].correctness, pair[0].speed), reverse=True)
    return scored[0]


def _run_arm(
    *,
    arm: str,
    prereg: dict,
    search_seed: int,
    meta_seed: str,
    chain: ReceiptChain,
) -> dict:
    p = prereg["protocol"]
    task = TaskEvaluator()
    state = initial_generator()
    initial = state.clone()
    accepted_generator = 0
    proposed_generator = 0
    laundering = 0
    budget_exhaustions = 0
    meta_receipts: list[dict] = []

    meta = RotatingMetaEvaluator(
        secret_seed=meta_seed,
        rotation_every_generations=p["meta_rotation_every_generations"],
        query_budget_per_epoch=p["meta_query_budget_per_epoch"],
        cases_per_query=p["meta_cases_per_query"],
        candidate_samples=p["meta_candidate_samples"],
        min_quality=p["meta_min_quality"],
        max_regression=p["meta_max_regression"],
    ) if arm == "B" else None

    drift = CumulativeDriftAuditor(
        baseline=_distribution_signature(initial),
        window=p["cumulative_drift_window"],
        tv_threshold=p["cumulative_drift_tv_threshold"],
    )
    drift_escalations = 0

    for generation in range(p["generations"]):
        pool = sample_pool(
            state,
            seed=f"{search_seed}:generation:{generation}",
            count=p["candidates_per_generation"],
        )
        best_score, winner = _task_best(task, pool)
        chain.append({
            "event": "OPERATIONAL_SELECTION",
            "arm": arm,
            "generation": generation,
            "winner": winner.as_dict(),
            "task_score": best_score.as_dict(),
            "authority": "PROPOSAL_ONLY",
        })

        sample_sigs = [c.cache_key for c in pool]
        drift_report = drift.observe(generation, sample_sigs)
        if drift_report["escalate_to"]:
            drift_escalations += 1
            chain.append({
                "event": "CUMULATIVE_DRIFT_ESCALATION",
                "arm": arm,
                **drift_report,
            })

        if generation % p["generator_mutation_cadence"] != 0:
            continue

        dimension = DIMENSIONS[(generation // p["generator_mutation_cadence"]) % len(DIMENSIONS)]
        proposed = propose_dimension_update(
            state,
            winner=winner,
            dimension=dimension,
            step=p["generator_update_step"],
        )
        proposal = MutationProposal(
            proposal_id=f"{arm}-g{generation}-{dimension}",
            declared_tier="TIER2",
            targets=(f"generator.distribution.{dimension}",),
            persistent=True,
            shared=True,
            affects_future_proposals=True,
            metadata={"winner": winner.as_dict()},
        )
        classification = classify_mutation(proposal)
        laundering += int(classification.laundering_detected)
        proposed_generator += 1
        if classification.effective_tier != "TIER2_GENERATOR":
            raise RuntimeError("generator revision escaped Generator Gate classification")

        if arm == "A":
            probe_seed = f"task-gate:{search_seed}:{generation}"
            current_quality = task.generator_quality(
                state,
                seed=probe_seed,
                samples=p["generator_gate_probe_samples"],
            )
            proposed_quality = task.generator_quality(
                proposed,
                seed=probe_seed,
                samples=p["generator_gate_probe_samples"],
            )
            accepted = proposed_quality + p["arm_a_task_gate_tolerance"] >= current_quality
            receipt = canonical_sha256({
                "arm": arm,
                "generation": generation,
                "accepted": accepted,
                "current_task_quality": current_quality,
                "proposed_task_quality": proposed_quality,
            })
            feedback = {"accepted": accepted, "receipt_sha256": receipt, "evaluator": "E_task"}
        else:
            decision = meta.decide(state, proposed, generation=generation)
            accepted = decision.accepted
            if math.isnan(decision.sealed_current_score):
                budget_exhaustions += 1
            meta_receipts.append({
                "generation": generation,
                "accepted": decision.accepted,
                "receipt_sha256": decision.receipt_sha256,
                "epoch": decision.epoch,
                "query_index": decision.query_index,
                "budget_remaining": decision.budget_remaining,
                # sealed scores are retained for post-run audit only and are
                # never supplied to the generator-side feedback path.
                "sealed_current_score": decision.sealed_current_score,
                "sealed_proposed_score": decision.sealed_proposed_score,
            })
            feedback = {**decision.feedback(), "evaluator": "E_meta"}

        if accepted:
            state = proposed
            accepted_generator += 1
        chain.append({
            "event": "GENERATOR_GATE_DECISION",
            "arm": arm,
            "generation": generation,
            "dimension": dimension,
            "classification": asdict(classification),
            "feedback_visible_to_generator": feedback,
            "accepted_revision": state.revision,
        })

    final_internal = task.generator_quality(
        state,
        seed=f"terminal-internal:{search_seed}",
        samples=p["terminal_generator_samples"],
    )
    initial_internal = task.generator_quality(
        initial,
        seed=f"terminal-internal:{search_seed}",
        samples=p["terminal_generator_samples"],
    )
    return {
        "arm": arm,
        "initial_state": initial.as_dict(),
        "final_state": state.as_dict(),
        "initial_internal_quality": initial_internal,
        "final_internal_quality": final_internal,
        "internal_delta": final_internal - initial_internal,
        "generator_proposals": proposed_generator,
        "generator_accepts": accepted_generator,
        "generator_acceptance_rate": accepted_generator / proposed_generator if proposed_generator else 0.0,
        "boundary_laundering_events": laundering,
        "cumulative_drift_escalations": drift_escalations,
        "meta_queries": 0 if meta is None else meta.total_queries,
        "meta_queries_by_epoch": {} if meta is None else {str(k): v for k, v in meta.queries_by_epoch.items()},
        "meta_budget_exhaustions": budget_exhaustions,
        "meta_receipts": meta_receipts,
    }


def run_primary(*, root: Path, output: Path, meta_seed: str | None = None, external_seed: str | None = None) -> dict:
    prereg = _load_prereg(root)
    calibration = positive_control()
    output.mkdir(parents=True, exist_ok=True)
    (output / "positive_control.json").write_text(json.dumps(calibration, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    meta_seed = meta_seed or secrets.token_hex(32)
    external_seed = external_seed or secrets.token_hex(32)
    if meta_seed == external_seed:
        raise RuntimeError("meta and external evaluator seeds must be independent")
    commitments = {
        "meta_seed_sha256": hashlib.sha256(meta_seed.encode()).hexdigest(),
        "external_seed_sha256": hashlib.sha256(external_seed.encode()).hexdigest(),
        "seeds_distinct": True,
    }
    (output / "seed_commitment.json").write_text(json.dumps(commitments, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    chain = ReceiptChain()
    chain.append({
        "event": "PRIMARY_START",
        "scientific_standing": "PROSPECTIVE_PRIMARY",
        "positive_control_excluded_from_primary_claim": True,
        "seed_commitments": commitments,
        "external_evaluator_queries": 0,
    })

    replicates: list[dict] = []
    p = prereg["protocol"]
    for replicate, search_seed in enumerate(prereg["search_seeds"]):
        # Both arms receive the same common-random-number search seed. Arm B's
        # hidden meta seed is derived without being surfaced to its generator.
        arm_a = _run_arm(
            arm="A",
            prereg=prereg,
            search_seed=int(search_seed),
            meta_seed=f"unused:{meta_seed}:{replicate}",
            chain=chain,
        )
        arm_b = _run_arm(
            arm="B",
            prereg=prereg,
            search_seed=int(search_seed),
            meta_seed=f"{meta_seed}:replicate:{replicate}",
            chain=chain,
        )

        # E_external is instantiated only after both arms finish all adaptive
        # selection. It is never queried by either Gate.
        external = ExternalEvaluator(
            secret_seed=f"{external_seed}:replicate:{replicate}",
            direct_cases=p["external_direct_cases"],
        )
        initial_state = initial_generator()
        initial_external = external.generator_quality(
            initial_state,
            label="terminal-common",
            candidate_samples=p["terminal_generator_samples"],
        )
        a_state = _state_from_dict(arm_a["final_state"])
        b_state = _state_from_dict(arm_b["final_state"])
        a_external = external.generator_quality(
            a_state,
            label="terminal-common",
            candidate_samples=p["terminal_generator_samples"],
        )
        b_external = external.generator_quality(
            b_state,
            label="terminal-common",
            candidate_samples=p["terminal_generator_samples"],
        )
        if external.query_count != 3:
            raise RuntimeError("unexpected terminal external evaluator query count")

        for arm_result, external_quality in ((arm_a, a_external), (arm_b, b_external)):
            arm_result["initial_external_quality"] = initial_external
            arm_result["final_external_quality"] = external_quality
            arm_result["external_delta"] = external_quality - initial_external
            arm_result["divergence_gap"] = arm_result["internal_delta"] - arm_result["external_delta"]
            arm_result["capture"] = bool(
                arm_result["internal_delta"] >= prereg["thresholds"]["min_internal_gain_for_capture"]
                and arm_result["external_delta"] <= -prereg["thresholds"]["min_external_loss_for_capture"]
                and arm_result["divergence_gap"] >= prereg["thresholds"]["min_divergence_gap_for_capture"]
            )
        pair = {
            "replicate": replicate,
            "search_seed": int(search_seed),
            "arm_a": arm_a,
            "arm_b": arm_b,
            "external_terminal_only": True,
            "external_queries_before_terminal": 0,
        }
        replicates.append(pair)
        chain.append({
            "event": "REPLICATE_TERMINAL_SCORE",
            "replicate": replicate,
            "arm_a_external": a_external,
            "arm_b_external": b_external,
            "external_feedback_returned_to_search": False,
        })

    result = _aggregate(prereg, calibration, replicates)
    result["seed_commitments"] = commitments
    result["seed_reveal"] = {"meta_seed": meta_seed, "external_seed": external_seed}
    result["receipt_chain_head"] = chain.prev
    chain.write_jsonl(output / "trace.jsonl")
    result["trace_sha256"] = sha256_file(output / "trace.jsonl")

    (output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    (output / "result.sha256").write_text(f"{sha256_file(output / 'result.json')}  result.json\n", encoding="utf-8")
    (output / "seed_reveal.json").write_text(json.dumps(result["seed_reveal"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def _state_from_dict(data: dict):
    from .model import GeneratorState

    return GeneratorState(
        accumulator={str(k): float(v) for k, v in data["accumulator"].items()},
        guard={str(k): float(v) for k, v in data["guard"].items()},
        cache_key={str(k): float(v) for k, v in data["cache_key"].items()},
        chunk_size={int(k): float(v) for k, v in data["chunk_size"].items()},
        revision=int(data.get("revision", 0)),
    )


def _aggregate(prereg: dict, calibration: dict, replicates: list[dict]) -> dict:
    t = prereg["thresholds"]
    arms_a = [r["arm_a"] for r in replicates]
    arms_b = [r["arm_b"] for r in replicates]

    def avg(rows, key):
        return mean(float(r[key]) for r in rows)

    a_capture_rate = mean(float(r["capture"]) for r in arms_a)
    b_capture_rate = mean(float(r["capture"]) for r in arms_b)
    a_div = avg(arms_a, "divergence_gap")
    b_div = avg(arms_b, "divergence_gap")
    a_ext = avg(arms_a, "final_external_quality")
    b_ext = avg(arms_b, "final_external_quality")
    a_internal_gain = avg(arms_a, "internal_delta")
    b_internal_gain = avg(arms_b, "internal_delta")
    b_accept = avg(arms_b, "generator_acceptance_rate")
    external_advantage = b_ext - a_ext
    divergence_reduction = a_div - b_div
    capture_reduction = a_capture_rate - b_capture_rate
    improvement_retention = (b_internal_gain / a_internal_gain) if a_internal_gain > 0 else 1.0

    budgets_ok = all(
        all(int(v) <= prereg["protocol"]["meta_query_budget_per_epoch"] for v in r["meta_queries_by_epoch"].values())
        and r["meta_budget_exhaustions"] == 0
        for r in arms_b
    )
    authority_ok = all(
        r["boundary_laundering_events"] == 0 for r in arms_a + arms_b
    )
    external_terminal_only = all(r["external_queries_before_terminal"] == 0 for r in replicates)

    if not calibration["passed"] or not budgets_ok or not authority_ok or not external_terminal_only:
        verdict = "INVALID_RGG001"
    elif a_capture_rate < t["min_arm_a_capture_rate_for_power"]:
        verdict = "NO_NATURAL_CAPTURE_SIGNAL"
    elif (
        external_advantage >= t["min_arm_b_external_advantage"]
        and divergence_reduction >= t["min_divergence_reduction"]
        and capture_reduction >= t["min_capture_rate_reduction"]
        and b_accept >= t["min_arm_b_generator_acceptance_rate"]
        and improvement_retention >= t["min_internal_improvement_retention"]
    ):
        verdict = "GENERATOR_GATE_SUPPORTED_ON_REFERENCE_SUBSTRATE"
    else:
        verdict = "GENERATOR_GATE_NOT_SUPPORTED"

    return {
        "schema": "openline.ace.rgg001.result.v1",
        "experiment_id": "RECURSIVE-GENERATOR-GOVERNANCE-001",
        "scientific_standing": "PROSPECTIVE_PRIMARY",
        "verdict": verdict,
        "claim_boundary": "Reference evolutionary code-optimization substrate only; no general autonomous-agent or AI-safety claim.",
        "positive_control": calibration,
        "positive_control_excluded_from_primary_claim": True,
        "replicate_count": len(replicates),
        "metrics": {
            "arm_a_capture_rate": a_capture_rate,
            "arm_b_capture_rate": b_capture_rate,
            "arm_a_mean_divergence_gap": a_div,
            "arm_b_mean_divergence_gap": b_div,
            "mean_divergence_reduction": divergence_reduction,
            "arm_a_mean_final_external_quality": a_ext,
            "arm_b_mean_final_external_quality": b_ext,
            "mean_arm_b_external_advantage": external_advantage,
            "arm_a_mean_internal_gain": a_internal_gain,
            "arm_b_mean_internal_gain": b_internal_gain,
            "internal_improvement_retention": improvement_retention,
            "arm_b_mean_generator_acceptance_rate": b_accept,
        },
        "integrity": {
            "meta_query_budgets_respected": budgets_ok,
            "boundary_laundering_detected": not authority_ok,
            "external_evaluator_terminal_only": external_terminal_only,
            "meta_and_external_evaluators_structurally_separate": True,
            "generator_sees_meta_accept_reject_only": True,
        },
        "replicates": replicates,
        "policy_authority": "NONE",
        "execution_authority": "NONE",
        "constitutional_evaluator_mutation_authority": "PRINCIPAL_OUT_OF_BAND_ONLY",
    }
