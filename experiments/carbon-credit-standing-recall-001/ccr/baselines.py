from __future__ import annotations

from .model import ClaimGraph, Prediction


def global_invalidation(
    graph: ClaimGraph, changed_artifacts: frozenset[str]
) -> Prediction:
    reopened = graph.claims if changed_artifacts else frozenset()
    return Prediction.build(claims=graph.claims, reopened=reopened)


def flat_registry(
    graph: ClaimGraph, changed_artifacts: frozenset[str]
) -> Prediction:
    reopened = {
        target
        for source, target in graph.edges
        if source in changed_artifacts and target in graph.claims
    }
    return Prediction.build(claims=graph.claims, reopened=reopened)
