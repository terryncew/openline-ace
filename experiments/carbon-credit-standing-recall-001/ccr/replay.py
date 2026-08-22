from __future__ import annotations

from .baselines import flat_registry, global_invalidation
from .engine import selective_reverification
from .metrics import score
from .model import ClaimGraph


def run_case(case: dict[str, object], oracle: dict[str, object]) -> dict[str, object]:
    graph = ClaimGraph.from_mapping(case)
    changed = frozenset(str(item) for item in case["changed_artifacts"])
    required = frozenset(str(item) for item in oracle["required_reopenings"])
    scored = frozenset(str(item) for item in oracle["scored_claims"])

    if graph.claims != scored:
        raise ValueError("case claims and oracle scored_claims must match exactly")

    methods = {
        "selective_reverification": selective_reverification(graph, changed),
        "global_invalidation": global_invalidation(graph, changed),
        "flat_registry": flat_registry(graph, changed),
    }

    result: dict[str, object] = {}
    for name, prediction in methods.items():
        result[name] = {
            "reopened": sorted(prediction.reopened),
            "retained": sorted(prediction.retained),
            "metrics": score(prediction, required),
        }
    return result
