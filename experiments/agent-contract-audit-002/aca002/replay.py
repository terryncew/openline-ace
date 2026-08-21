from __future__ import annotations

from typing import Any

from .task import expected_token_hash


def replay_verifier(results: list[dict[str, Any]], tasks: list[dict[str, Any]]) -> dict[str, Any]:
    by_task = {t["task_id"]: t for t in tasks}
    mismatches = []
    for i, result in enumerate(results):
        task = by_task.get(result["task_id"])
        if task is None:
            mismatches.append({"index": i, "reason": "unknown_task"})
            continue
        expected_success = result["final_output_sha256"] == expected_token_hash(task)
        if result["verifier"]["id"] != "aca002-token-verifier-v1":
            mismatches.append({"index": i, "reason": "verifier_id"})
        elif result["verifier"]["success"] is not expected_success:
            mismatches.append({"index": i, "reason": "verifier_success"})
    return {"rows": len(results), "mismatches": mismatches, "verified": not mismatches}
