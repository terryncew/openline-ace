from __future__ import annotations
from collections import defaultdict, deque
from .model import ClaimGraph, ReplayPrediction

def selective_reopen(graph: ClaimGraph, changed_artifacts: frozenset[str]) -> ReplayPrediction:
    """Reopen only claims reachable from changed artifact roots."""
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
    return ReplayPrediction.build(claims=graph.claims, reopened=reopened)
