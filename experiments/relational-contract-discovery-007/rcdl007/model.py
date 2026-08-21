from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class Standing(str, Enum):
    NUISANCE = "NUISANCE"
    NATIVE = "NATIVE"
    IMPOSED = "IMPOSED"
    MIXED = "MIXED"
    INVALID = "INVALID"


RELATIONS = ("freshness", "lineage", "submit_gate", "timeout_gate")
NATIVE_RELATIONS = frozenset({"freshness", "lineage"})
IMPOSED_RELATIONS = frozenset({"submit_gate", "timeout_gate"})


@dataclass(frozen=True)
class Probe:
    probe_id: str
    repairs: frozenset[str]


@dataclass(frozen=True)
class RawObservation:
    external_success: bool
    event_count_bucket: int
    surface_tag: str


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    faults: frozenset[str]
    nuisance_seed: int


@dataclass(frozen=True)
class QueryEvent:
    probe_id: str
    observation: RawObservation


@dataclass(frozen=True)
class PolicyDecision:
    standing: Standing
    queries: tuple[QueryEvent, ...]
    explanation_code: str


QueryFn = Callable[[str], RawObservation]
