from __future__ import annotations

from typing import Any


def contract_manifests(candidates: list[dict[str, Any]], grade: dict[str, Any], provider_verified: bool) -> list[dict[str, Any]]:
    by_id = {c["candidate_id"]: c for c in candidates}
    out = []
    for g in grade["grades"]:
        if g["standing"] != "SUPPORTED":
            continue
        c = by_id[g["candidate_id"]]
        out.append({
            "schema": "openline.agent-contract.v1",
            "candidate_id": c["candidate_id"],
            "surface_id": c["surface_id"],
            "text": c["text"],
            "standing": "SUPPORTED",
            "scope": c["scope"],
            "evidence": {
                "pairs": g["pairs"],
                "active_minus_sham_failure_delta": g["active_minus_sham_failure_delta"],
                "restoration_minus_active_success_delta": g["restoration_minus_active_success_delta"],
            },
            "external_provider_lane": bool(provider_verified),
            "provider_provenance": "runner-declared",
            "policy_authority": "NONE",
            "compiler_eligible": False,
            "note": "Standing is audit evidence only; downstream receiver policy remains separate."
        })
    return out
