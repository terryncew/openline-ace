from __future__ import annotations

from collections import defaultdict, deque

from .model import ClaimGraph, Prediction


def selective_reverification(
    graph: ClaimGraph, changed_artifacts: frozenset[str]
) -> Prediction:
    """Reopen claim descendants of changed artifacts; retain the rest."""
    adjacency: dict[str, list[str]] = defaultdict(list)
    for source, target in graph.edges:
        adjacency[source].append(target)

    queue = deque(sorted(changed_artifacts))
    seen = set(changed_artifacts)
    reopened: set[str] = set()

    while queue:
        node = queue.popleft()
        for target in sorted(adjacency.get(node, ())):
            if target in seen:
                continue
            seen.add(target)
            queue.append(target)
            if target in graph.claims:
                reopened.add(target)

    return Prediction.build(claims=graph.claims, reopened=reopened)
