"""Semantics-preserving trace transformations used as nuisance controls."""

from __future__ import annotations

from typing import Any

from .trace import Trace

NODE_FIELDS = {"candidate", "leader"}
NODE_LIST_FIELDS = {"voters", "leaders"}


def rename_nodes(trace: Trace) -> Trace:
    names = sorted({event.node for event in trace.events if event.node != "system"})
    mapping = {name: f"actor_{index}" for index, name in enumerate(names)}
    document = trace.to_dict()
    document["run_id"] = f"{trace.run_id}-renamed"
    for event in document["events"]:
        event["node"] = mapping.get(event["node"], event["node"])
        attrs: dict[str, Any] = event["attrs"]
        for field in NODE_FIELDS:
            if field in attrs:
                attrs[field] = mapping.get(attrs[field], attrs[field])
        for field in NODE_LIST_FIELDS:
            if field in attrs and isinstance(attrs[field], list):
                attrs[field] = [mapping.get(item, item) for item in attrs[field]]
    return Trace.from_dict(document)


def renumber_events(trace: Trace) -> Trace:
    document = trace.to_dict()
    document["run_id"] = f"{trace.run_id}-renumbered"
    for index, event in enumerate(document["events"]):
        event["event_id"] = f"opaque_{index + 1000}"
    return Trace.from_dict(document)


def reorder_object_keys(trace: Trace) -> Trace:
    document = trace.to_dict()
    document["run_id"] = f"{trace.run_id}-reordered"
    for event in document["events"]:
        event["attrs"] = dict(reversed(list(event["attrs"].items())))
    document["metadata"] = dict(reversed(list(document["metadata"].items())))
    return Trace.from_dict(document)


def nuisance_variants(trace: Trace) -> tuple[Trace, ...]:
    return (rename_nodes(trace), renumber_events(trace), reorder_object_keys(trace))

