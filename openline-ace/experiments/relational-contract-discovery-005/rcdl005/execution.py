"""Two deterministic execution adapters plus matched active/sham probes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .canonical import canonical_digest
from .domain import ACTION_BY_ID, IMPLEMENTATIONS, Scenario, behavior_preserved

TRACE_SCHEMA = "rcdl.causal-probe-trace/0.5"


@dataclass(frozen=True)
class ProbeTrace:
    implementation: str
    arm: str
    action_id: str
    document: dict[str, Any]

    @property
    def digest(self) -> str:
        return canonical_digest(self.document)


@dataclass(frozen=True)
class ParsedProbe:
    failed: bool
    energy_units: int
    scenario_commitment: str


@dataclass(frozen=True)
class ProbePair:
    active: ProbeTrace
    sham: ProbeTrace
    active_outcome: ParsedProbe
    sham_outcome: ParsedProbe


@dataclass(frozen=True)
class RecoveryResult:
    restored_relation: str
    immediate_preservation: bool
    eventual_preservation: bool
    horizon: int


def _commitment(scenario: Scenario) -> str:
    return canonical_digest(
        {
            "scenario_id": scenario.id,
            "hypothesis_id": scenario.hypothesis_id,
            "nuisance_seed": scenario.nuisance_seed,
        }
    )


def _energy(action_id: str) -> int:
    return 100 + 37 * len(ACTION_BY_ID[action_id])


def _ledger_document(
    scenario: Scenario,
    action_id: str,
    arm: str,
    outcome_failed: bool,
) -> dict[str, Any]:
    nuisance = scenario.nuisance_seed % 4
    events = [
        {
            "kind": "snapshot",
            "sequence": 1,
            "attrs": {"surface": f"ledger-{nuisance}", "state": "baseline"},
        },
        {
            "kind": "mutation",
            "sequence": 2,
            "attrs": {
                "mode": "causal-sever" if arm == "active" else "surface-sham",
                "energy_units": _energy(action_id),
            },
        },
        {
            "kind": "external_oracle",
            "sequence": 3,
            "attrs": {"behavior": "failed" if outcome_failed else "preserved"},
        },
    ]
    if nuisance % 2:
        events.insert(
            1,
            {
                "kind": "irrelevant_annotation",
                "sequence": 0,
                "attrs": {"format": "compact" if nuisance == 1 else "pretty"},
            },
        )
    return {
        "schema": TRACE_SCHEMA,
        "implementation": "ledger",
        "scenario_commitment": _commitment(scenario),
        "action_id": action_id,
        "arm": arm,
        "events": events,
    }


def _queue_document(
    scenario: Scenario,
    action_id: str,
    arm: str,
    outcome_failed: bool,
) -> dict[str, Any]:
    nuisance = scenario.nuisance_seed % 4
    messages = [
        {"topic": "state.read", "body": {"phase": "baseline"}},
        {
            "topic": "proxy.applied",
            "body": {
                "class": "edge" if arm == "active" else "nuisance",
                "cost": _energy(action_id),
            },
        },
        {
            "topic": "oracle.result",
            "body": {"ok": not outcome_failed},
        },
    ]
    if nuisance % 2:
        messages.append(
            {"topic": "audit.noop", "body": {"layout": ["b", "a"] if nuisance == 1 else ["a", "b"]}}
        )
    return {
        "schema": TRACE_SCHEMA,
        "implementation": "queue",
        "scenario_commitment": _commitment(scenario),
        "action_id": action_id,
        "arm": arm,
        "messages": messages,
    }


def execute_probe(
    scenario: Scenario,
    action_id: str,
    arm: str,
    implementation: str,
) -> ProbeTrace:
    if action_id not in ACTION_BY_ID:
        raise ValueError(f"unknown action: {action_id}")
    if arm not in {"active", "sham"}:
        raise ValueError("arm must be active or sham")
    if implementation not in IMPLEMENTATIONS:
        raise ValueError(f"unknown implementation: {implementation}")
    broken = ACTION_BY_ID[action_id] if arm == "active" else frozenset()
    outcome_failed = not behavior_preserved(scenario.hypothesis.family, broken)
    document = (
        _ledger_document(scenario, action_id, arm, outcome_failed)
        if implementation == "ledger"
        else _queue_document(scenario, action_id, arm, outcome_failed)
    )
    return ProbeTrace(implementation, arm, action_id, document)


def parse_probe(trace: ProbeTrace) -> ParsedProbe:
    document = trace.document
    expected_keys = {
        "schema",
        "implementation",
        "scenario_commitment",
        "action_id",
        "arm",
        "events" if trace.implementation == "ledger" else "messages",
    }
    if set(document) != expected_keys or document.get("schema") != TRACE_SCHEMA:
        raise ValueError("trace envelope closure failed")
    if (
        document.get("implementation") != trace.implementation
        or document.get("action_id") != trace.action_id
        or document.get("arm") != trace.arm
    ):
        raise ValueError("trace envelope binding failed")
    if trace.implementation == "ledger":
        mutation = [item for item in document["events"] if item.get("kind") == "mutation"]
        oracle = [item for item in document["events"] if item.get("kind") == "external_oracle"]
        if len(mutation) != 1 or len(oracle) != 1:
            raise ValueError("ledger trace cardinality failed")
        energy = mutation[0].get("attrs", {}).get("energy_units")
        behavior = oracle[0].get("attrs", {}).get("behavior")
        if behavior not in {"preserved", "failed"}:
            raise ValueError("ledger oracle value failed")
        failed_value = behavior == "failed"
    else:
        mutation = [item for item in document["messages"] if item.get("topic") == "proxy.applied"]
        oracle = [item for item in document["messages"] if item.get("topic") == "oracle.result"]
        if len(mutation) != 1 or len(oracle) != 1:
            raise ValueError("queue trace cardinality failed")
        energy = mutation[0].get("body", {}).get("cost")
        ok = oracle[0].get("body", {}).get("ok")
        if not isinstance(ok, bool):
            raise ValueError("queue oracle value failed")
        failed_value = not ok
    if isinstance(energy, bool) or not isinstance(energy, int) or energy <= 0:
        raise ValueError("probe energy is invalid")
    return ParsedProbe(failed_value, energy, str(document["scenario_commitment"]))


def execute_pair(scenario: Scenario, action_id: str, implementation: str) -> ProbePair:
    active = execute_probe(scenario, action_id, "active", implementation)
    sham = execute_probe(scenario, action_id, "sham", implementation)
    active_outcome = parse_probe(active)
    sham_outcome = parse_probe(sham)
    if active_outcome.energy_units != sham_outcome.energy_units:
        raise RuntimeError("active and sham intervention energy differs")
    if active_outcome.scenario_commitment != sham_outcome.scenario_commitment:
        raise RuntimeError("active and sham scenario commitments differ")
    return ProbePair(active, sham, active_outcome, sham_outcome)


def execute_recovery(
    scenario: Scenario, action_id: str, restored_relation: str
) -> RecoveryResult:
    broken = ACTION_BY_ID[action_id]
    if restored_relation not in broken:
        raise ValueError("recovery must restore a broken relation")
    remaining = broken - {restored_relation}
    immediate = behavior_preserved(scenario.hypothesis.family, remaining)
    return RecoveryResult(
        restored_relation,
        immediate,
        True,
        1 if immediate else len(broken),
    )

