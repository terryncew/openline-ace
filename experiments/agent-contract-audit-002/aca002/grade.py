from __future__ import annotations

from typing import Any

from .pin import load_a001


def grade_external(candidates: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    model, audit = load_a001()
    policy = model.AuditPolicy()
    a001_candidates = []
    for c in candidates:
        a001_candidates.append({
            "candidate_id": c["candidate_id"],
            "text": c["text"],
            "scope": c["scope"],
            "relation": c["relation"],
            "source": {"type": "llm_proposer", "authority": "NONE"},
            "interventions": c["interventions"],
        })
    arm_results = [
        model.ArmResult.from_mapping({
            "candidate_id": r["candidate_id"],
            "pair_id": r["pair_id"],
            "task_id": r["task_id"],
            "seed": r["seed"],
            "arm": r["arm"],
            "verifier_id": r["verifier"]["id"],
            "verifier_success": r["verifier"]["success"],
            "runner_status": r["runner_status"],
            "trace_sha256": r["trace_sha256"],
        }) for r in results
    ]
    graded = audit.grade_audit(a001_candidates, arm_results, policy)
    surface_by_id = {c["candidate_id"]: c["surface_id"] for c in candidates}
    for grade in graded["grades"]:
        grade["surface_id"] = surface_by_id[grade["candidate_id"]]
    graded["engine"] = "frozen-aca001"
    graded["authority"] = "NONE"
    return graded
