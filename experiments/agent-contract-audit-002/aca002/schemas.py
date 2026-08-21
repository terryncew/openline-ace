from __future__ import annotations

from typing import Any, Mapping

FORBIDDEN_BLIND_KEYS = {
    "current_token", "stale_token", "ground_truth", "expected_standing",
    "oracle_label", "verifier_success", "standing", "verdict", "hidden_truth"
}


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def assert_blind(value: Any) -> None:
    hits = sorted(set(_walk_keys(value)) & FORBIDDEN_BLIND_KEYS)
    if hits:
        raise ValueError(f"blind packet contains adjudication/private keys: {hits}")


def validate_proposed_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {"candidate_id", "text", "scope", "relation", "evidence_refs"}
    missing = required - set(value)
    if missing:
        raise ValueError(f"missing proposed candidate fields: {sorted(missing)}")
    assert_blind(value)
    cid = str(value["candidate_id"])
    if not cid or len(cid) > 96:
        raise ValueError("invalid candidate_id")
    refs = value["evidence_refs"]
    if not isinstance(refs, list) or not refs:
        raise ValueError("evidence_refs must be a non-empty list")
    return {
        "candidate_id": cid,
        "text": str(value["text"]),
        "scope": str(value["scope"]),
        "relation": str(value["relation"]),
        "evidence_refs": [str(x) for x in refs],
        "source": {"type": "llm_proposer", "authority": "NONE"},
    }


def validate_compiler_mapping(value: Mapping[str, Any], allowed_surfaces: set[str]) -> dict[str, str]:
    if set(value) != {"candidate_id", "surface_id"}:
        raise ValueError("compiler mapping must contain exactly candidate_id and surface_id")
    surface = str(value["surface_id"])
    if surface not in allowed_surfaces:
        raise ValueError(f"unknown intervention surface: {surface}")
    return {"candidate_id": str(value["candidate_id"]), "surface_id": surface}
