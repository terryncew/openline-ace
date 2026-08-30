from __future__ import annotations

from .model import Proposal


GENERATOR_PREFIXES = (
    "generator/",
    ".openline/generator/",
    ".openline/evaluators/",
    ".openline/policy/",
    "agent/search/",
    "agent/retrieval/",
)


def effective_mutation_tier(proposal: Proposal) -> str:
    if proposal.generator_surface:
        return "TIER2_GENERATOR"
    for path in proposal.changed_paths:
        normalized = path.lstrip("./")
        if any(normalized.startswith(prefix) for prefix in GENERATOR_PREFIXES):
            return "TIER2_GENERATOR"
    if proposal.mutation_tier not in {"TIER1_OPERATIONAL", "TIER2_GENERATOR"}:
        return "TIER2_GENERATOR"
    return proposal.mutation_tier
