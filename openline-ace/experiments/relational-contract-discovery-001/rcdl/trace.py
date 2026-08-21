"""Normalized execution traces used by clause evaluators."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import canonical_json, load_json_bytes

TRACE_SCHEMA = "rcdl.trace/0.1"
RESERVED_FIELDS = {"event_id", "run_id", "step", "node", "kind"}


class TraceValidationError(ValueError):
    """Raised when trace structure or ordering is invalid."""


@dataclass(frozen=True)
class Event:
    run_id: str
    event_id: str
    step: int
    node: str
    kind: str
    attrs: dict[str, Any]

    def get(self, field: str, default: Any = None) -> Any:
        if field == "run_id":
            return self.run_id
        if field == "event_id":
            return self.event_id
        if field == "step":
            return self.step
        if field == "node":
            return self.node
        if field == "kind":
            return self.kind
        return self.attrs.get(field, default)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "step": self.step,
            "node": self.node,
            "kind": self.kind,
            "attrs": copy.deepcopy(self.attrs),
        }


@dataclass(frozen=True)
class Trace:
    run_id: str
    metadata: dict[str, Any]
    events: tuple[Event, ...]

    @classmethod
    def from_dict(cls, document: dict[str, Any]) -> "Trace":
        if not isinstance(document, dict):
            raise TraceValidationError("$: trace must be an object")
        if set(document) != {"schema", "run_id", "metadata", "events"}:
            raise TraceValidationError("$: expected schema, run_id, metadata, and events only")
        if document["schema"] != TRACE_SCHEMA:
            raise TraceValidationError(f"$.schema: expected {TRACE_SCHEMA!r}")
        run_id = document["run_id"]
        if not isinstance(run_id, str) or not run_id:
            raise TraceValidationError("$.run_id: expected non-empty string")
        metadata = document["metadata"]
        if not isinstance(metadata, dict):
            raise TraceValidationError("$.metadata: expected object")
        canonical_json(metadata)
        raw_events = document["events"]
        if not isinstance(raw_events, list):
            raise TraceValidationError("$.events: expected array")

        events: list[Event] = []
        seen_ids: set[str] = set()
        previous_step = -1
        for index, raw in enumerate(raw_events):
            path = f"$.events[{index}]"
            if not isinstance(raw, dict) or set(raw) != {
                "event_id",
                "step",
                "node",
                "kind",
                "attrs",
            }:
                raise TraceValidationError(f"{path}: invalid event shape")
            event_id = raw["event_id"]
            if not isinstance(event_id, str) or not event_id or event_id in seen_ids:
                raise TraceValidationError(f"{path}.event_id: empty or duplicate")
            seen_ids.add(event_id)
            step = raw["step"]
            if isinstance(step, bool) or not isinstance(step, int) or step <= previous_step:
                raise TraceValidationError(f"{path}.step: steps must be strictly increasing")
            previous_step = step
            node = raw["node"]
            kind = raw["kind"]
            if not isinstance(node, str) or not node:
                raise TraceValidationError(f"{path}.node: expected non-empty string")
            if not isinstance(kind, str) or not kind:
                raise TraceValidationError(f"{path}.kind: expected non-empty string")
            attrs = raw["attrs"]
            if not isinstance(attrs, dict):
                raise TraceValidationError(f"{path}.attrs: expected object")
            collision = RESERVED_FIELDS & attrs.keys()
            if collision:
                raise TraceValidationError(f"{path}.attrs: reserved fields {sorted(collision)}")
            canonical_json(attrs)
            events.append(Event(run_id, event_id, step, node, kind, copy.deepcopy(attrs)))
        return cls(run_id, copy.deepcopy(metadata), tuple(events))

    @classmethod
    def from_path(cls, path: str | Path) -> "Trace":
        value = load_json_bytes(Path(path).read_bytes())
        if not isinstance(value, dict):
            raise TraceValidationError("$: trace must be an object")
        return cls.from_dict(value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TRACE_SCHEMA,
            "run_id": self.run_id,
            "metadata": copy.deepcopy(self.metadata),
            "events": [event.to_dict() for event in self.events],
        }

    def write(self, path: str | Path) -> None:
        Path(path).write_bytes(canonical_json(self.to_dict()) + b"\n")

