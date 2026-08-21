from __future__ import annotations

from typing import Any

ARMS = ("baseline", "active", "sham", "restoration")


def build_schedule(
    candidates: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    *,
    pairs: int = 64,
    seed_base: int = 820000,
) -> list[dict[str, Any]]:
    if pairs < 64:
        raise ValueError("A-001 frozen standing engine requires at least 64 pairs")
    if not tasks:
        raise ValueError("no tasks")
    rows = []
    for c_idx, candidate in enumerate(candidates):
        for p in range(pairs):
            task = tasks[p % len(tasks)]
            pair_id = f"{candidate['candidate_id']}:{task['task_id']}:{p:04d}"
            seed = seed_base + c_idx * 100000 + p
            for arm in ARMS:
                if arm == "baseline":
                    intervention = {"op": "none"}
                else:
                    intervention = dict(candidate["interventions"][arm])
                rows.append({
                    "protocol": "openline.agent-contract-audit.runner-request.v2",
                    "candidate_id": candidate["candidate_id"],
                    "surface_id": candidate["surface_id"],
                    "pair_id": pair_id,
                    "task_id": task["task_id"],
                    "seed": seed,
                    "arm": arm,
                    "intervention": intervention,
                    "policy_authority": "NONE",
                })
    return rows
