from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping, Sequence

from .model import ArmResult, AuditPolicy, validate_candidate
from .stats import paired_bootstrap_mean_ci


def _group_pairs(results: Iterable[ArmResult]) -> dict[str, dict[str, ArmResult]]:
    pairs: dict[str, dict[str, ArmResult]] = defaultdict(dict)
    for result in results:
        if result.arm in pairs[result.pair_id]:
            raise ValueError(f"duplicate arm {result.arm} for {result.pair_id}")
        pairs[result.pair_id][result.arm] = result
    return dict(pairs)


def grade_candidate(
    candidate: Mapping[str, Any],
    results: Sequence[ArmResult],
    policy: AuditPolicy,
) -> dict[str, Any]:
    candidate = validate_candidate(candidate)
    candidate_id = str(candidate["candidate_id"])
    scoped = [r for r in results if r.candidate_id == candidate_id]
    pairs = _group_pairs(scoped)
    complete = []
    for pair_id, arms in pairs.items():
        if set(arms) != {"baseline", "active", "sham", "restoration"}:
            raise ValueError(f"incomplete pair {pair_id}: {sorted(arms)}")
        verifier_ids = {r.verifier_id for r in arms.values()}
        if len(verifier_ids) != 1:
            raise ValueError(f"verifier changed within pair {pair_id}")
        complete.append(arms)

    if len(complete) < policy.min_pairs:
        return {
            "candidate_id": candidate_id,
            "standing": "UNDECIDABLE_INSUFFICIENT_PAIRS",
            "pairs": len(complete),
            "policy": policy.as_dict(),
        }

    baseline_success = [1.0 if p["baseline"].verifier_success else 0.0 for p in complete]
    active_fail = [0.0 if p["active"].verifier_success else 1.0 for p in complete]
    sham_fail = [0.0 if p["sham"].verifier_success else 1.0 for p in complete]
    restore_success = [1.0 if p["restoration"].verifier_success else 0.0 for p in complete]

    baseline_success_rate = sum(baseline_success) / len(complete)
    sham_failure_rate = sum(sham_fail) / len(complete)

    delta_values = [a - s for a, s in zip(active_fail, sham_fail)]
    recovery_values = [
        restore - (1.0 - fail)
        for restore, fail in zip(restore_success, active_fail)
    ]

    delta_mean, delta_low, delta_high = paired_bootstrap_mean_ci(
        delta_values,
        samples=policy.bootstrap_samples,
        alpha=policy.bootstrap_alpha,
        seed_material=f"{candidate_id}:active-minus-sham",
    )
    recovery_mean, recovery_low, recovery_high = paired_bootstrap_mean_ci(
        recovery_values,
        samples=policy.bootstrap_samples,
        alpha=policy.bootstrap_alpha,
        seed_material=f"{candidate_id}:restoration-minus-active",
    )

    if baseline_success_rate < policy.baseline_success_floor:
        standing = "UNDECIDABLE_FLAKY_BASELINE"
    elif sham_failure_rate > policy.sham_failure_ceiling:
        standing = "UNDECIDABLE_SHAM_EFFECT"
    elif delta_low >= policy.effect_margin and recovery_low >= policy.effect_margin:
        standing = "SUPPORTED"
    elif delta_low >= policy.effect_margin:
        standing = "UNDECIDABLE_NO_RESTORATION"
    elif delta_low >= -policy.equivalence_band and delta_high <= policy.equivalence_band:
        standing = "REJECTED_RITUAL"
    else:
        standing = "UNDECIDABLE_NOISE_FLOOR"

    return {
        "candidate_id": candidate_id,
        "standing": standing,
        "pairs": len(complete),
        "baseline_success_rate": baseline_success_rate,
        "sham_failure_rate": sham_failure_rate,
        "active_minus_sham_failure_delta": {
            "mean": delta_mean, "ci_low": delta_low, "ci_high": delta_high
        },
        "restoration_minus_active_success_delta": {
            "mean": recovery_mean, "ci_low": recovery_low, "ci_high": recovery_high
        },
        "verifier_ids": sorted({p["baseline"].verifier_id for p in complete}),
        "policy": policy.as_dict(),
    }


def grade_audit(
    candidates: Sequence[Mapping[str, Any]],
    results: Sequence[ArmResult],
    policy: AuditPolicy,
) -> dict[str, Any]:
    grades = [grade_candidate(c, results, policy) for c in candidates]
    return {
        "policy": policy.as_dict(),
        "grades": grades,
        "supported": [g["candidate_id"] for g in grades if g["standing"] == "SUPPORTED"],
        "rejected_rituals": [
            g["candidate_id"] for g in grades if g["standing"] == "REJECTED_RITUAL"
        ],
        "undecidable": [
            g["candidate_id"]
            for g in grades
            if g["standing"].startswith("UNDECIDABLE")
        ],
        "authority": "NONE",
    }
