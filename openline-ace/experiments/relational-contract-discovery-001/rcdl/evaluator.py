"""Bounded RCDL clause evaluation over normalized traces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .model import Clause
from .trace import Event, Trace

_MISSING = object()


@dataclass(frozen=True)
class Evaluation:
    clause_id: str
    clause_digest: str
    passed: bool
    trigger_count: int
    support_count: int
    violation_count: int
    violations: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "clause_id": self.clause_id,
            "clause_digest": self.clause_digest,
            "passed": self.passed,
            "trigger_count": self.trigger_count,
            "support_count": self.support_count,
            "violation_count": self.violation_count,
            "violations": [dict(item) for item in self.violations],
        }


def _matches(event: Event, where: dict[str, Any]) -> bool:
    return all(event.get(field, _MISSING) == value for field, value in where.items())


def _joins(candidate: Event, trigger: Event, joins: dict[str, str]) -> bool:
    for candidate_field, trigger_field in joins.items():
        left = candidate.get(candidate_field, _MISSING)
        right = trigger.get(trigger_field, _MISSING)
        if left is _MISSING or right is _MISSING or left != right:
            return False
    return True


def _triggers(clause: Clause, trace: Trace) -> list[Event]:
    trigger = clause.document["trigger"]
    return [
        event
        for event in trace.events
        if event.kind == trigger["event"] and _matches(event, trigger.get("where", {}))
    ]


def _violation(trigger: Event, reason: str, **details: Any) -> dict[str, Any]:
    value = {"event_id": trigger.event_id, "step": trigger.step, "reason": reason}
    value.update(details)
    return value


def _threshold(requirement: dict[str, Any], trace: Trace) -> int:
    value = requirement["threshold"]
    if isinstance(value, int):
        return value
    field = value["field"]
    size = trace.metadata.get(field)
    if isinstance(size, bool) or not isinstance(size, int) or size < 1:
        raise ValueError(f"trace metadata {field!r} must be a positive integer")
    return size // 2 + 1


def evaluate(clause: Clause, trace: Trace) -> Evaluation:
    """Evaluate a validated clause without consulting any oracle output."""

    triggers = _triggers(clause, trace)
    requirement = clause.document["require"]
    op = requirement["op"]
    violations: list[dict[str, Any]] = []
    support_count = 0

    if op == "unique_per_key":
        groups: dict[tuple[Any, ...], tuple[Any, ...]] = {}
        first_events: dict[tuple[Any, ...], str] = {}
        for trigger in triggers:
            key = tuple(trigger.get(field, _MISSING) for field in requirement["key"])
            value = tuple(trigger.get(field, _MISSING) for field in requirement["value"])
            if _MISSING in key or _MISSING in value:
                violations.append(_violation(trigger, "missing_group_field"))
                continue
            if key not in groups:
                groups[key] = value
                first_events[key] = trigger.event_id
                support_count += 1
            elif groups[key] != value:
                violations.append(
                    _violation(
                        trigger,
                        "non_unique_value",
                        first_event_id=first_events[key],
                    )
                )

    elif op in {"exists_before", "precedes_without"}:
        for trigger in triggers:
            candidates = [
                event
                for event in trace.events
                if event.step < trigger.step
                and event.kind == requirement["event"]
                and _matches(event, requirement.get("where", {}))
                and _joins(event, trigger, requirement["joins"])
            ]
            if not candidates:
                violations.append(_violation(trigger, "required_predecessor_absent"))
                continue
            if op == "exists_before":
                support_count += 1
                continue
            predecessor = max(candidates, key=lambda item: item.step)
            blocker = requirement["blocker"]
            blocked = False
            for event in trace.events:
                if not predecessor.step < event.step < trigger.step:
                    continue
                if event.kind != blocker["event"] or not _matches(event, blocker.get("where", {})):
                    continue
                if "joins" in blocker and not _joins(event, trigger, blocker["joins"]):
                    continue
                blocked = True
                break
            if blocked:
                violations.append(_violation(trigger, "intervening_blocker"))
            else:
                support_count += 1

    elif op == "count_distinct_before":
        needed = _threshold(requirement, trace)
        for trigger in triggers:
            values = {
                event.get(requirement["distinct"], _MISSING)
                for event in trace.events
                if event.step < trigger.step
                and event.kind == requirement["event"]
                and _matches(event, requirement.get("where", {}))
                and _joins(event, trigger, requirement["joins"])
            }
            values.discard(_MISSING)
            if len(values) < needed:
                violations.append(
                    _violation(
                        trigger,
                        "cardinality_below_threshold",
                        observed=len(values),
                        required=needed,
                    )
                )
            else:
                support_count += 1

    elif op == "eventually_within":
        horizon = requirement["horizon"]
        assumptions = requirement.get("assumptions", [])
        for trigger in triggers:
            if assumptions and not all(trace.metadata.get(name) is True for name in assumptions):
                continue
            matches = [
                event
                for event in trace.events
                if trigger.step < event.step <= trigger.step + horizon
                and event.kind == requirement["event"]
                and _matches(event, requirement.get("where", {}))
                and _joins(event, trigger, requirement["joins"])
            ]
            if matches:
                support_count += 1
            else:
                violations.append(_violation(trigger, "bounded_progress_absent", horizon=horizon))
    else:  # pragma: no cover - Clause validation prevents this path.
        raise ValueError(f"unsupported requirement operation: {op}")

    return Evaluation(
        clause_id=clause.id,
        clause_digest=clause.digest,
        passed=not violations,
        trigger_count=len(triggers),
        support_count=support_count,
        violation_count=len(violations),
        violations=tuple(violations),
    )

