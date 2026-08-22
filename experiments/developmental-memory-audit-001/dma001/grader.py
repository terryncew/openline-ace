from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path

ARMS = ("baseline", "sham", "active", "restoration")

@dataclass(frozen=True)
class Thresholds:
    min_replicates_per_arm: int = 8
    min_baseline_success_rate: float = 0.75
    min_sham_success_rate: float = 0.75
    min_active_minus_sham_failure_delta: float = 0.40
    min_restoration_minus_active_success_delta: float = 0.40

def load_results(path: str | Path):
    rows = []
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("arm") not in ARMS:
            raise ValueError(f"line {line_no}: invalid arm")
        if row.get("success") not in (True, False):
            raise ValueError(f"line {line_no}: success must be boolean")
        if not isinstance(row.get("candidate_id"), str) or not row["candidate_id"]:
            raise ValueError(f"line {line_no}: candidate_id required")
        if not isinstance(row.get("replicate_id"), str) or not row["replicate_id"]:
            raise ValueError(f"line {line_no}: replicate_id required")
        rows.append(row)
    return rows

def _rate(values):
    return sum(1 for v in values if v) / len(values)

def grade_candidate(rows, candidate_id: str, thresholds: Thresholds = Thresholds()):
    grouped = defaultdict(list)
    seen = set()
    for row in rows:
        if row["candidate_id"] != candidate_id:
            continue
        key = (row["arm"], row["replicate_id"])
        if key in seen:
            raise ValueError(f"duplicate arm/replicate for {candidate_id}: {key}")
        seen.add(key)
        grouped[row["arm"]].append(row["success"])

    counts = {arm: len(grouped[arm]) for arm in ARMS}
    if any(counts[a] < thresholds.min_replicates_per_arm for a in ARMS):
        return {
            "candidate_id": candidate_id,
            "standing": "INCOMPLETE",
            "reason": "insufficient_replicates_or_missing_restoration",
            "counts": counts,
            "policy_authority": "NONE",
        }

    success = {arm: _rate(grouped[arm]) for arm in ARMS}
    failure = {arm: 1.0 - success[arm] for arm in ARMS}
    active_minus_sham_failure = failure["active"] - failure["sham"]
    restoration_minus_active_success = success["restoration"] - success["active"]

    metrics = {
        "success_rate": success,
        "active_minus_sham_failure_delta": round(active_minus_sham_failure, 6),
        "restoration_minus_active_success_delta": round(restoration_minus_active_success, 6),
    }

    if success["baseline"] < thresholds.min_baseline_success_rate:
        standing, reason = "ABSTAIN_BASELINE_UNSTABLE", "baseline_below_floor"
    elif success["sham"] < thresholds.min_sham_success_rate:
        standing, reason = "ABSTAIN_SHAM_DAMAGE", "matched_sham_below_floor"
    elif active_minus_sham_failure < thresholds.min_active_minus_sham_failure_delta:
        standing, reason = "REJECTED_RITUAL", "active_perturbation_not_specific_enough"
    elif restoration_minus_active_success < thresholds.min_restoration_minus_active_success_delta:
        standing, reason = "UNRESOLVED_NO_RECOVERY", "restoration_did_not_recover"
    else:
        standing, reason = "SUPPORTED_LOAD_BEARING", "perturbation_specific_and_restoration_recovers"

    return {
        "candidate_id": candidate_id,
        "standing": standing,
        "reason": reason,
        "counts": counts,
        "metrics": metrics,
        "policy_authority": "NONE",
    }

def grade_file(path: str | Path):
    rows = load_results(path)
    candidate_ids = sorted({r["candidate_id"] for r in rows})
    return [grade_candidate(rows, c) for c in candidate_ids]
