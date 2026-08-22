from __future__ import annotations
from .model import ClaimGraph, ReplayPrediction

def global_invalidation(graph: ClaimGraph, changed_artifacts: frozenset[str]) -> ReplayPrediction:
    reopened = graph.claims if changed_artifacts else frozenset()
    return ReplayPrediction.build(claims=graph.claims, reopened=reopened)

def flat_latest_state(graph: ClaimGraph, changed_artifacts: frozenset[str]) -> ReplayPrediction:
    reopened = {target for source, target in graph.edges if source in changed_artifacts and target in graph.claims}
    return ReplayPrediction.build(claims=graph.claims, reopened=reopened)
