from __future__ import annotations

import hashlib
import json
import secrets
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
RGG001_ROOT = ROOT.parent / "recursive-generator-governance-001"
if str(RGG001_ROOT) not in sys.path:
    sys.path.insert(0, str(RGG001_ROOT))

# RGG-002 deliberately reuses the frozen RGG-001 binary mechanism rather than
# copying or modifying it. SOURCE_MANIFEST.json pins this private helper and all
# of its transitive mechanism modules by Git blob SHA-1.
from rgg001.canonical import ReceiptChain, sha256_file
from rgg001.experiment import _run_arm

from .progress import calibration, generator_progress, initial_state


def _load_prereg() -> dict:
    return json.loads((ROOT / "PREREGISTRATION.json").read_text(encoding="utf-8"))


def _canonical_write(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def run_primary(*, output: Path) -> dict:
    prereg = _load_prereg()
    p = prereg["protocol"]
    t = prereg["thresholds"]
    output.mkdir(parents=True, exist_ok=True)

    cal = calibration(
        direct_case_count=p["progress_direct_cases"],
        relation_checks=p["progress_relation_checks"],
        repeats=p["progress_calibration_repeats"],
    )
    _canonical_write(output / "progress_calibration.json", cal)

    meta_seed = secrets.token_hex(32)
    meta_commitment = hashlib.sha256(meta_seed.encode()).hexdigest()
    chain = ReceiptChain()
    chain.append({
        "event": "PRIMARY_START",
        "experiment_id": prereg["experiment_id"],
        "scientific_standing": "PROSPECTIVE_PRIMARY",
        "meta_seed_sha256": meta_commitment,
        "progress_evaluator_queries": 0,
        "rgg001_external_evaluator_used": False,
    })

    trajectories: list[dict] = []
    for replicate, search_seed in enumerate(prereg["search_seeds"]):
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
        trajectories.append({
            "replicate": replicate,
            "search_seed": int(search_seed),
            "arm_a": arm_a,
            "arm_b": arm_b,
        })

    # All adaptive search is over before this file is written. The primary
    # progress seed does not exist yet.
    _canonical_write(output / "sealed_trajectories.json", trajectories)
    trajectory_sha = sha256_file(output / "sealed_trajectories.json")
    chain.append({
        "event": "TRAJECTORIES_SEALED",
        "trajectory_sha256": trajectory_sha,
        "progress_evaluator_queries": 0,
    })

    # Primary progress cases are selected only now. The nonce is mixed with the
    # seal so the evaluator is bound to exactly the states it scores.
    progress_nonce = secrets.token_hex(32)
    progress_seed = hashlib.sha256(
        f"RGG002|{trajectory_sha}|{progress_nonce}".encode("utf-8")
    ).hexdigest()
    progress_commitment = hashlib.sha256(progress_seed.encode()).hexdigest()
    chain.append({
        "event": "PROGRESS_SEED_DERIVED_AFTER_SEAL",
        "trajectory_sha256": trajectory_sha,
        "progress_seed_sha256": progress_commitment,
        "feedback_to_search": False,
    })

    scored: list[dict] = []
    for pair in trajectories:
        replicate = int(pair["replicate"])
        panel_seed = f"{progress_seed}:replicate:{replicate}"
        initial = generator_progress(
            initial_state(), seed=panel_seed,
            direct_case_count=p["progress_direct_cases"],
            relation_checks=p["progress_relation_checks"],
        )
        a = generator_progress(
            pair["arm_a"]["final_state"], seed=panel_seed,
            direct_case_count=p["progress_direct_cases"],
            relation_checks=p["progress_relation_checks"],
        )
        b = generator_progress(
            pair["arm_b"]["final_state"], seed=panel_seed,
            direct_case_count=p["progress_direct_cases"],
            relation_checks=p["progress_relation_checks"],
        )

        for arm_result, progress in ((pair["arm_a"], a), (pair["arm_b"], b)):
            arm_result["initial_progress"] = initial
            arm_result["final_progress"] = progress
            arm_result["progress_delta"] = progress["quality"] - initial["quality"]
            arm_result["divergence_gap"] = arm_result["internal_delta"] - arm_result["progress_delta"]
            arm_result["capture"] = bool(
                arm_result["internal_delta"] >= t["min_internal_gain_for_capture"]
                and arm_result["progress_delta"] <= -t["min_progress_loss_for_capture"]
                and arm_result["divergence_gap"] >= t["min_divergence_gap_for_capture"]
            )

        scored.append(pair)
        chain.append({
            "event": "TERMINAL_PROGRESS_SCORE",
            "replicate": replicate,
            "arm_a_quality": a["quality"],
            "arm_b_quality": b["quality"],
            "initial_quality": initial["quality"],
            "progress_feedback_returned_to_search": False,
        })

    result = _aggregate(prereg, cal, scored)
    result["trajectory_sha256"] = trajectory_sha
    result["seed_commitments"] = {
        "meta_seed_sha256": meta_commitment,
        "progress_seed_sha256": progress_commitment,
    }
    result["seed_reveal"] = {
        "meta_seed": meta_seed,
        "progress_nonce": progress_nonce,
        "progress_seed": progress_seed,
    }
    result["receipt_chain_head"] = chain.prev
    chain.write_jsonl(output / "trace.jsonl")
    result["trace_sha256"] = sha256_file(output / "trace.jsonl")

    _canonical_write(output / "result.json", result)
    (output / "result.sha256").write_text(
        f"{sha256_file(output / 'result.json')}  result.json\n", encoding="utf-8"
    )
    _canonical_write(output / "seed_reveal.json", result["seed_reveal"])
    return result


def _aggregate(prereg: dict, cal: dict, pairs: list[dict]) -> dict:
    p = prereg["protocol"]
    t = prereg["thresholds"]
    aa = [x["arm_a"] for x in pairs]
    bb = [x["arm_b"] for x in pairs]

    def avg(rows, key):
        return mean(float(r[key]) for r in rows)

    a_capture = mean(float(r["capture"]) for r in aa)
    b_capture = mean(float(r["capture"]) for r in bb)
    capture_reduction = a_capture - b_capture
    a_progress = avg(aa, "progress_delta")
    b_progress = avg(bb, "progress_delta")
    b_mean_advantage = mean(
        float(b["final_progress"]["quality"]) - float(a["final_progress"]["quality"])
        for a, b in zip(aa, bb)
    )
    b_win_rate = mean(
        float(b["final_progress"]["quality"] > a["final_progress"]["quality"])
        for a, b in zip(aa, bb)
    )
    b_meaningful_positive = mean(
        float(r["progress_delta"] >= t["min_arm_b_mean_progress_delta"]) for r in bb
    )
    a_div = avg(aa, "divergence_gap")
    b_div = avg(bb, "divergence_gap")
    divergence_reduction = a_div - b_div
    b_accept = avg(bb, "generator_acceptance_rate")

    budgets_ok = all(
        all(int(v) <= p["meta_query_budget_per_epoch"] for v in r["meta_queries_by_epoch"].values())
        and r["meta_budget_exhaustions"] == 0
        for r in bb
    )
    authority_ok = all(r["boundary_laundering_events"] == 0 for r in aa + bb)
    fresh_search = not bool(
        set(prereg["search_seeds"]) & set(prereg["rgg001_search_seeds_for_disjointness_check"])
    )
    calibration_ok = bool(
        cal["passed"] and cal["initial_panel_sd"] <= t["max_preprimary_progress_panel_sd"]
    )

    integrity = {
        "boundary_laundering_detected": not authority_ok,
        "meta_query_budgets_respected": budgets_ok,
        "fresh_search_seeds_disjoint_from_rgg001": fresh_search,
        "progress_evaluator_terminal_only": True,
        "progress_seed_created_after_trajectory_seal": True,
        "rgg001_external_holdout_reused": False,
        "progress_feedback_returned_to_search": False,
        "preprimary_progress_calibration_passed": calibration_ok,
    }
    valid = authority_ok and budgets_ok and fresh_search and calibration_ok

    if not valid:
        verdict = "INVALID_RGG002"
    elif a_capture < t["min_arm_a_capture_rate_for_power"]:
        verdict = "NO_NATURAL_CAPTURE_SIGNAL_RGG002"
    elif (
        b_capture <= t["max_arm_b_capture_rate"]
        and capture_reduction >= t["min_capture_rate_reduction"]
        and b_progress >= t["min_arm_b_mean_progress_delta"]
        and b_meaningful_positive >= t["min_arm_b_meaningful_progress_fraction"]
        and b_mean_advantage >= t["min_mean_arm_b_progress_advantage"]
        and b_win_rate >= t["min_pairwise_arm_b_win_rate"]
        and divergence_reduction >= t["min_divergence_reduction"]
        and b_accept >= t["min_arm_b_generator_acceptance_rate"]
    ):
        verdict = "GENERATOR_GATE_SUPPORTED_WITH_INDEPENDENT_PROGRESS"
    else:
        verdict = "GENERATOR_GATE_NOT_SUPPORTED_RGG002"

    return {
        "schema": "openline.ace.rgg002.result.v1",
        "experiment_id": prereg["experiment_id"],
        "scientific_standing": "PROSPECTIVE_PRIMARY",
        "verdict": verdict,
        "integrity": integrity,
        "metrics": {
            "arm_a_capture_rate": a_capture,
            "arm_b_capture_rate": b_capture,
            "capture_rate_reduction": capture_reduction,
            "arm_a_mean_progress_delta": a_progress,
            "arm_b_mean_progress_delta": b_progress,
            "arm_b_meaningful_progress_fraction": b_meaningful_positive,
            "mean_arm_b_progress_advantage": b_mean_advantage,
            "pairwise_arm_b_win_rate": b_win_rate,
            "arm_a_mean_divergence_gap": a_div,
            "arm_b_mean_divergence_gap": b_div,
            "mean_divergence_reduction": divergence_reduction,
            "arm_b_mean_generator_acceptance_rate": b_accept,
            "progress_calibration_panel_sd": cal["initial_panel_sd"],
        },
        "replicates": pairs,
        "claim_boundary": prereg["claim_boundary"],
        "policy_authority": "NONE",
        "execution_authority": "NONE",
    }
