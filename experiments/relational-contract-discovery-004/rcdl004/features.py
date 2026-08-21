"""Generic sequence and graph features with identity values erased.

The feature code knows event structure, ordering, and generic equality.  It has
no clause ids, intervention hooks, or workflow-specific target rules.
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from typing import Any, Callable

from rcdl.canonical import canonical_digest
from rcdl.trace import Event, Trace

MAX_RELATION_DISTANCE = 32
WL_ROUNDS = 2
RAW_VALUE_KEYS = frozenset({"event_id", "run_id", "seed", "hook", "arm"})


def _distance_bucket(distance: int) -> str:
    if distance <= 1:
        return "1"
    if distance <= 3:
        return "2-3"
    if distance <= 7:
        return "4-7"
    if distance <= 15:
        return "8-15"
    return "16+"


def _identity_like(key: str) -> bool:
    return key in RAW_VALUE_KEYS or key.endswith("_id") or "hash" in key or "digest" in key


def _safe_value(key: str, value: Any) -> str | None:
    if _identity_like(key):
        return None
    if value is None or isinstance(value, bool):
        return repr(value)
    if isinstance(value, int):
        if -16 <= value <= 16:
            return str(value)
        return "positive-large" if value > 0 else "negative-large"
    if isinstance(value, str) and len(value) <= 32:
        return value
    return None


def _canonical_actors(trace: Trace) -> dict[str, str]:
    result: dict[str, str] = {}
    for event in trace.events:
        if event.node not in result:
            result[event.node] = f"actor{len(result)}"
    return result


def _event_label(event: Event, actor: str) -> str:
    scalars = [
        f"{key}={safe}"
        for key, value in sorted(event.attrs.items())
        if (safe := _safe_value(key, value)) is not None
    ]
    return "|".join((event.kind, actor, *scalars))


def sequence_features(trace: Trace) -> dict[str, int]:
    """Return order and generic equality features, never raw identities."""

    result: Counter[str] = Counter()
    actors = _canonical_actors(trace)
    events = trace.events
    kinds = [event.kind for event in events]
    for index, event in enumerate(events):
        actor = actors[event.node]
        result[f"event:{event.kind}"] += 1
        result[f"event-actor:{event.kind}@{actor}"] += 1
        for key, value in sorted(event.attrs.items()):
            safe = _safe_value(key, value)
            if safe is not None:
                result[f"scalar:{event.kind}:{key}={safe}"] += 1
        if index:
            result[f"bigram:{kinds[index - 1]}>{event.kind}"] += 1
        if index >= 2:
            result[f"trigram:{kinds[index - 2]}>{kinds[index - 1]}>{event.kind}"] += 1

    for left_index, left in enumerate(events):
        left_task = left.attrs.get("task_id")
        for right_index in range(left_index + 1, min(len(events), left_index + MAX_RELATION_DISTANCE + 1)):
            right = events[right_index]
            distance = right_index - left_index
            right_task = right.attrs.get("task_id")
            same_task = left_task is not None and left_task == right_task
            if same_task:
                result[f"same-task:{left.kind}>{right.kind}"] += 1
                result[
                    f"same-task-distance:{left.kind}>{right.kind}:{_distance_bucket(distance)}"
                ] += 1
            common = sorted(set(left.attrs) & set(right.attrs))
            for key in common:
                if key == "task_id" or same_task:
                    relation = "eq" if left.attrs[key] == right.attrs[key] else "neq"
                    result[f"relation:{key}:{left.kind}>{right.kind}:{relation}"] += 1
                    result[
                        f"relation-distance:{key}:{left.kind}>{right.kind}:{relation}:{_distance_bucket(distance)}"
                    ] += 1
    return dict(result)


def graph_features(trace: Trace) -> dict[str, int]:
    """Return a two-round Weisfeiler-Lehman event-graph representation."""

    events = trace.events
    actors = _canonical_actors(trace)
    labels = {
        index: hashlib.sha256(_event_label(event, actors[event.node]).encode("utf-8")).hexdigest()[:24]
        for index, event in enumerate(events)
    }
    neighbors: dict[int, list[tuple[str, int]]] = defaultdict(list)
    for index in range(len(events) - 1):
        neighbors[index].append(("next-out", index + 1))
        neighbors[index + 1].append(("next-in", index))
    for left_index, left in enumerate(events):
        left_task = left.attrs.get("task_id")
        for right_index in range(left_index + 1, min(len(events), left_index + MAX_RELATION_DISTANCE + 1)):
            right = events[right_index]
            right_task = right.attrs.get("task_id")
            same_task = left_task is not None and left_task == right_task
            if same_task:
                neighbors[left_index].append(("same-task", right_index))
                neighbors[right_index].append(("same-task", left_index))
            if same_task and "patch_hash" in left.attrs and "patch_hash" in right.attrs:
                edge = "same-patch" if left.attrs["patch_hash"] == right.attrs["patch_hash"] else "different-patch"
                neighbors[left_index].append((edge, right_index))
                neighbors[right_index].append((edge, left_index))

    result: Counter[str] = Counter()
    for round_index in range(WL_ROUNDS + 1):
        for label in labels.values():
            result[f"wl{round_index}:{label}"] += 1
        if round_index == WL_ROUNDS:
            break
        updated: dict[int, str] = {}
        for node, label in labels.items():
            neighborhood = sorted(f"{edge}:{labels[target]}" for edge, target in neighbors[node])
            updated[node] = canonical_digest({"self": label, "neighbors": neighborhood})[:24]
        labels = updated
    result["graph:event-count"] = len(events)
    result["graph:edge-count"] = sum(len(items) for items in neighbors.values())
    return dict(result)


def combined_features(trace: Trace) -> dict[str, int]:
    result = {f"seq:{key}": value for key, value in sequence_features(trace).items()}
    result.update({f"graph:{key}": value for key, value in graph_features(trace).items()})
    return result


def task_segments(trace: Trace) -> tuple[Trace, ...]:
    """Partition a trace by opaque task-identity equality, preserving order."""

    order: list[Any] = []
    groups: dict[Any, list[Event]] = {}
    for event in trace.events:
        task_id = event.attrs.get("task_id")
        if task_id is None:
            raise ValueError("task-bag representation requires task_id on every event")
        if task_id not in groups:
            groups[task_id] = []
            order.append(task_id)
        groups[task_id].append(event)
    return tuple(
        Trace(f"opaque-segment-{index}", {}, tuple(groups[task_id]))
        for index, task_id in enumerate(order)
    )


FEATURE_EXTRACTORS: dict[str, Callable[[Trace], dict[str, int]]] = {
    "generic_relational_sequence": sequence_features,
    "weisfeiler_lehman_event_graph": graph_features,
    "combined_sequence_graph": combined_features,
}


def feature_schema_digest() -> str:
    return canonical_digest(
        {
            "schema": "rcdl.generic-relational-features/0.1",
            "extractors": sorted(FEATURE_EXTRACTORS),
            "max_relation_distance": MAX_RELATION_DISTANCE,
            "wl_rounds": WL_ROUNDS,
            "identity_values": "ERASED",
            "actor_names": "FIRST_OCCURRENCE_CANONICALIZED",
        }
    )
