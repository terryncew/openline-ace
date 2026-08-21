from __future__ import annotations

from typing import Any

from .schemas import validate_compiler_mapping, validate_proposed_candidate


def compile_candidates(
    proposed: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
    catalog: dict[str, Any],
) -> list[dict[str, Any]]:
    surfaces = {s["surface_id"]: s for s in catalog["surfaces"]}
    by_candidate = {m["candidate_id"]: m for m in (
        validate_compiler_mapping(x, set(surfaces)) for x in mappings
    )}
    compiled = []
    seen_surfaces: set[str] = set()
    for raw in proposed:
        candidate = validate_proposed_candidate(raw)
        cid = candidate["candidate_id"]
        if cid not in by_candidate:
            continue
        surface_id = by_candidate[cid]["surface_id"]
        if surface_id in seen_surfaces:
            continue
        seen_surfaces.add(surface_id)
        surface = surfaces[surface_id]
        compiled.append({
            **candidate,
            "surface_id": surface_id,
            "interventions": {
                "active": {"op": surface["active_op"]},
                "sham": {"op": surface["sham_op"]},
                "restoration": {"op": surface["restoration_op"]},
            },
            "compiler": {"authority": "NONE", "mode": "catalog_mapping"},
        })
    return compiled
