"""Validated RCDL 0.1 clause objects."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import canonical_digest, canonical_json, load_json_bytes

CLAUSE_SCHEMA = "rcdl.clause/0.1"
CLAUSE_KINDS = {"guard", "integrity", "order", "progress"}
REQUIREMENT_OPS = {
    "unique_per_key",
    "exists_before",
    "count_distinct_before",
    "precedes_without",
    "eventually_within",
}
MAX_JOIN_FIELDS = 4
MAX_KEY_FIELDS = 4
FIELD_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,127}$")
FORBIDDEN_DISCOVERY_FIELDS = {
    "arm",
    "external_behavior",
    "external_failure",
    "failed_properties",
    "failure_label",
    "hook",
    "intervention_arm",
    "oracle_passed",
    "oracle_result",
    "standing",
    "verdict",
}


class ClauseValidationError(ValueError):
    """Raised when a clause is outside the frozen RCDL 0.1 grammar."""


def _exact_keys(value: dict[str, Any], required: set[str], optional: set[str], path: str) -> None:
    missing = required - value.keys()
    unknown = value.keys() - required - optional
    if missing:
        raise ClauseValidationError(f"{path}: missing keys {sorted(missing)}")
    if unknown:
        raise ClauseValidationError(f"{path}: unknown keys {sorted(unknown)}")


def _field(value: Any, path: str) -> str:
    if not isinstance(value, str) or not FIELD_RE.fullmatch(value):
        raise ClauseValidationError(f"{path}: invalid field name")
    if value in FORBIDDEN_DISCOVERY_FIELDS:
        raise ClauseValidationError(f"{path}: outcome or intervention labels are unavailable")
    return value


def _symbol(value: Any, path: str) -> str:
    if not isinstance(value, str) or not FIELD_RE.fullmatch(value):
        raise ClauseValidationError(f"{path}: invalid symbol")
    return value


def _event_name(value: Any, path: str) -> str:
    return _field(value, path)


def _scalar(value: Any, path: str) -> None:
    if value is None or isinstance(value, (bool, int, str)):
        return
    raise ClauseValidationError(f"{path}: predicate constants must be scalar")


def _where(value: Any, path: str) -> None:
    if not isinstance(value, dict):
        raise ClauseValidationError(f"{path}: expected object")
    if len(value) > 6:
        raise ClauseValidationError(f"{path}: at most six predicate constants are allowed")
    for key, item in value.items():
        _field(key, f"{path}.{key}")
        _scalar(item, f"{path}.{key}")


def _joins(value: Any, path: str) -> None:
    if not isinstance(value, dict) or not value:
        raise ClauseValidationError(f"{path}: expected a non-empty object")
    if len(value) > MAX_JOIN_FIELDS:
        raise ClauseValidationError(f"{path}: at most {MAX_JOIN_FIELDS} joins are allowed")
    for left, right in value.items():
        _field(left, f"{path}.{left}")
        _field(right, f"{path}.{left}")


def _field_list(value: Any, path: str) -> None:
    if not isinstance(value, list) or not value or len(value) > MAX_KEY_FIELDS:
        raise ClauseValidationError(
            f"{path}: expected one to {MAX_KEY_FIELDS} field names"
        )
    if len(set(value)) != len(value):
        raise ClauseValidationError(f"{path}: duplicate field names")
    for index, item in enumerate(value):
        _field(item, f"{path}[{index}]")


def _validate_trigger(trigger: Any) -> None:
    if not isinstance(trigger, dict):
        raise ClauseValidationError("$.trigger: expected object")
    _exact_keys(trigger, {"event"}, {"where"}, "$.trigger")
    _event_name(trigger["event"], "$.trigger.event")
    _where(trigger.get("where", {}), "$.trigger.where")


def _validate_requirement(requirement: Any) -> None:
    if not isinstance(requirement, dict):
        raise ClauseValidationError("$.require: expected object")
    op = requirement.get("op")
    if op not in REQUIREMENT_OPS:
        raise ClauseValidationError(f"$.require.op: unsupported operation {op!r}")

    if op == "unique_per_key":
        _exact_keys(requirement, {"op", "key", "value"}, set(), "$.require")
        _field_list(requirement["key"], "$.require.key")
        _field_list(requirement["value"], "$.require.value")
        return

    if op == "exists_before":
        _exact_keys(requirement, {"op", "event", "joins"}, {"where"}, "$.require")
        _event_name(requirement["event"], "$.require.event")
        _joins(requirement["joins"], "$.require.joins")
        _where(requirement.get("where", {}), "$.require.where")
        return

    if op == "count_distinct_before":
        _exact_keys(
            requirement,
            {"op", "event", "joins", "distinct", "threshold"},
            {"where"},
            "$.require",
        )
        _event_name(requirement["event"], "$.require.event")
        _joins(requirement["joins"], "$.require.joins")
        _where(requirement.get("where", {}), "$.require.where")
        _field(requirement["distinct"], "$.require.distinct")
        threshold = requirement["threshold"]
        if isinstance(threshold, int) and not isinstance(threshold, bool):
            if threshold < 1:
                raise ClauseValidationError("$.require.threshold: must be positive")
        elif isinstance(threshold, dict):
            _exact_keys(threshold, {"op", "field"}, set(), "$.require.threshold")
            if threshold["op"] != "majority":
                raise ClauseValidationError("$.require.threshold.op: only majority is allowed")
            _field(threshold["field"], "$.require.threshold.field")
        else:
            raise ClauseValidationError("$.require.threshold: invalid threshold")
        return

    if op == "precedes_without":
        _exact_keys(
            requirement,
            {"op", "event", "joins", "blocker"},
            {"where"},
            "$.require",
        )
        _event_name(requirement["event"], "$.require.event")
        _joins(requirement["joins"], "$.require.joins")
        _where(requirement.get("where", {}), "$.require.where")
        blocker = requirement["blocker"]
        if not isinstance(blocker, dict):
            raise ClauseValidationError("$.require.blocker: expected object")
        _exact_keys(blocker, {"event"}, {"where", "joins"}, "$.require.blocker")
        _event_name(blocker["event"], "$.require.blocker.event")
        _where(blocker.get("where", {}), "$.require.blocker.where")
        if "joins" in blocker:
            _joins(blocker["joins"], "$.require.blocker.joins")
        return

    _exact_keys(
        requirement,
        {"op", "event", "joins", "horizon"},
        {"where", "assumptions"},
        "$.require",
    )
    _event_name(requirement["event"], "$.require.event")
    _joins(requirement["joins"], "$.require.joins")
    _where(requirement.get("where", {}), "$.require.where")
    horizon = requirement["horizon"]
    if isinstance(horizon, bool) or not isinstance(horizon, int) or not 1 <= horizon <= 10_000:
        raise ClauseValidationError("$.require.horizon: expected integer in [1, 10000]")
    assumptions = requirement.get("assumptions", [])
    if not isinstance(assumptions, list) or len(assumptions) > 4:
        raise ClauseValidationError("$.require.assumptions: expected at most four field names")
    for index, item in enumerate(assumptions):
        _field(item, f"$.require.assumptions[{index}]")


def _validate_intervention(intervention: Any) -> None:
    if not isinstance(intervention, dict):
        raise ClauseValidationError("$.intervention: expected object")
    _exact_keys(
        intervention,
        {"hook", "active", "sham", "energy"},
        set(),
        "$.intervention",
    )
    _symbol(intervention["hook"], "$.intervention.hook")
    _symbol(intervention["active"], "$.intervention.active")
    _symbol(intervention["sham"], "$.intervention.sham")
    energy = intervention["energy"]
    if isinstance(energy, bool) or not isinstance(energy, int) or not 1 <= energy <= 100:
        raise ClauseValidationError("$.intervention.energy: expected integer in [1, 100]")


@dataclass(frozen=True)
class Clause:
    """A validated canonical clause."""

    document: dict[str, Any]

    @classmethod
    def from_dict(cls, document: dict[str, Any]) -> "Clause":
        if not isinstance(document, dict):
            raise ClauseValidationError("$: clause must be an object")
        _exact_keys(
            document,
            {"schema", "id", "kind", "trigger", "require", "intervention"},
            {"description"},
            "$",
        )
        if document["schema"] != CLAUSE_SCHEMA:
            raise ClauseValidationError(f"$.schema: expected {CLAUSE_SCHEMA!r}")
        if not isinstance(document["id"], str) or not ID_RE.fullmatch(document["id"]):
            raise ClauseValidationError("$.id: invalid clause identifier")
        if document["kind"] not in CLAUSE_KINDS:
            raise ClauseValidationError("$.kind: invalid clause kind")
        if "description" in document:
            description = document["description"]
            if not isinstance(description, str) or not 1 <= len(description) <= 400:
                raise ClauseValidationError("$.description: expected 1 to 400 characters")
        _validate_trigger(document["trigger"])
        _validate_requirement(document["require"])
        _validate_intervention(document["intervention"])
        canonical_json(document)
        return cls(copy.deepcopy(document))

    @classmethod
    def from_path(cls, path: str | Path) -> "Clause":
        value = load_json_bytes(Path(path).read_bytes())
        if not isinstance(value, dict):
            raise ClauseValidationError("$: clause must be an object")
        return cls.from_dict(value)

    @property
    def id(self) -> str:
        return self.document["id"]

    @property
    def kind(self) -> str:
        return self.document["kind"]

    @property
    def hook(self) -> str:
        return self.document["intervention"]["hook"]

    @property
    def digest(self) -> str:
        return canonical_digest(self.document)

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self.document)
