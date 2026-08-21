from __future__ import annotations

import hashlib
from typing import Any

from .schedule import build_schedule
from .task import observation_for


def _h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def conformance_results(candidates: list[dict[str, Any]], tasks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    schedule = build_schedule(candidates, tasks, pairs=64)
    by_task = {t["task_id"]: t for t in tasks}
    rows = []
    for req in schedule:
        task = by_task[req["task_id"]]
        obs = observation_for(task, req["intervention"]["op"])
        # The fixture relay follows only the ticket value. This validates mechanics,
        # not external LLM behavior.
        final = obs["value"]
        success = final == task["current_token"]
        trace = f"{req['pair_id']}|{req['arm']}|{obs['value']}|{obs['marker']}|{obs['padding']}"
        rows.append({
            "protocol": "openline.agent-contract-audit.runner-result.v2",
            "candidate_id": req["candidate_id"],
            "surface_id": req["surface_id"],
            "pair_id": req["pair_id"],
            "task_id": req["task_id"],
            "seed": req["seed"],
            "arm": req["arm"],
            "runner_status": "ok",
            "verifier": {"id": "aca002-token-verifier-v1", "success": success},
            "trace_sha256": _h(trace),
            "final_output_sha256": _h(final),
            "provider": {"kind": "fixture", "model": "deterministic-relay", "external": False},
        })
    return schedule, rows
