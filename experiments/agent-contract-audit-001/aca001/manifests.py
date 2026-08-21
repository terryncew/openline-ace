from __future__ import annotations

from typing import Any, Mapping, Sequence


def _atoms(candidate: Mapping[str, Any]) -> frozenset[str]:
    relation = candidate.get("relation", {})
    atoms = relation.get("atoms", []) if isinstance(relation, dict) else []
    return frozenset(str(atom) for atom in atoms)


def reduce_supported(
    candidates: Sequence[Mapping[str, Any]],
    grades: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {str(c["candidate_id"]): c for c in candidates}
    supported = [g for g in grades if g.get("standing") == "SUPPORTED"]
    kept: list[Mapping[str, Any]] = []
    for grade in supported:
        candidate = by_id[str(grade["candidate_id"])]
        atoms = _atoms(candidate)
        redundant = False
        for other_grade in supported:
            if other_grade is grade:
                continue
            other = by_id[str(other_grade["candidate_id"])]
            if other.get("scope") != candidate.get("scope"):
                continue
            other_atoms = _atoms(other)
            if other_atoms and atoms and other_atoms < atoms:
                redundant = True
                break
        if not redundant:
            kept.append(grade)

    manifests = []
    for grade in kept:
        candidate = by_id[str(grade["candidate_id"])]
        manifests.append({
            "schema": "openline.agent-contract-manifest.v1",
            "candidate_id": candidate["candidate_id"],
            "clause": candidate["text"],
            "scope": candidate["scope"],
            "relation": candidate["relation"],
            "proposer": candidate["source"],
            "interventions": candidate["interventions"],
            "standing": grade["standing"],
            "pairs": grade["pairs"],
            "active_minus_sham_failure_delta": grade["active_minus_sham_failure_delta"],
            "restoration_minus_active_success_delta": grade["restoration_minus_active_success_delta"],
            "verifier_ids": grade["verifier_ids"],
            "policy_authority": "NONE",
            "compiler_eligible": False,
            "runtime_authority": "NONE",
            "reopening_conditions": [
                "verifier changes",
                "workflow scope changes",
                "effect no longer clears frozen margin on fresh rollouts",
                "matched sham begins causing material failure",
                "restoration stops predicting recovery",
            ],
        })
    return manifests
