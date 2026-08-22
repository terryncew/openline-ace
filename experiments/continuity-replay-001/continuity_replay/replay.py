from __future__ import annotations
from .baselines import flat_latest_state, global_invalidation
from .engine import selective_reopen
from .metrics import score
from .model import ClaimGraph

METHODS = {
    "continuity_observer": selective_reopen,
    "global_invalidation": global_invalidation,
    "flat_latest_state": flat_latest_state,
}

def evaluate_case(case: dict[str, object], warranted: frozenset[str]) -> dict[str, object]:
    graph = ClaimGraph.from_mapping(case["graph"])
    changed = frozenset(str(item) for item in case["observed_changed_paths"])
    outputs = {}
    for name, method in METHODS.items():
        prediction = method(graph, changed)
        outputs[name] = {
            "reopened": sorted(prediction.reopened),
            "retained": sorted(prediction.retained),
            "metrics": score(prediction, warranted),
        }
    return outputs
