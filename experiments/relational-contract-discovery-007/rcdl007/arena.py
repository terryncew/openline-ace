from __future__ import annotations

from itertools import combinations

from .canonical import digest
from .model import (
    IMPOSED_RELATIONS,
    NATIVE_RELATIONS,
    RELATIONS,
    Probe,
    RawObservation,
    Scenario,
    Standing,
)


PROBES = tuple(
    Probe(f"probe-{index:02d}", frozenset(repairs))
    for index, repairs in enumerate(
        list(combinations(RELATIONS, 1)) + list(combinations(RELATIONS, 2))
    )
)
PROBE_BY_ID = {probe.probe_id: probe for probe in PROBES}

DEVELOPMENT_FAULTS = (
    frozenset(),
    frozenset({"freshness"}),
    frozenset({"lineage"}),
    frozenset({"submit_gate"}),
    frozenset({"timeout_gate"}),
    frozenset({"freshness", "submit_gate"}),
    frozenset({"lineage", "timeout_gate"}),
)

_ALL_FAULTS = tuple(
    frozenset(items)
    for size in range(len(RELATIONS) + 1)
    for items in combinations(RELATIONS, size)
)
EVALUATION_FAULTS = (frozenset(),) + tuple(
    faults for faults in _ALL_FAULTS if faults not in DEVELOPMENT_FAULTS
)


def standing_for_faults(faults: frozenset[str]) -> Standing:
    if not faults:
        return Standing.NUISANCE
    has_native = bool(faults & NATIVE_RELATIONS)
    has_imposed = bool(faults & IMPOSED_RELATIONS)
    if has_native and has_imposed:
        return Standing.MIXED
    if has_native:
        return Standing.NATIVE
    if has_imposed:
        return Standing.IMPOSED
    return Standing.INVALID


def predicted_success(faults: frozenset[str], repairs: frozenset[str]) -> bool:
    return faults.issubset(repairs)


def passive_success(faults: frozenset[str]) -> bool:
    return not faults


def _surface(seed: int, scenario_id: str, probe_id: str, adapter: str, success: bool) -> RawObservation:
    token = digest(
        {
            "adapter": adapter,
            "probe_id": probe_id,
            "scenario_id": scenario_id,
            "seed": seed,
            "success": success,
        }
    )
    return RawObservation(
        external_success=success,
        event_count_bucket=2 + (int(token[:8], 16) % 5),
        surface_tag=token[8:20],
    )


def passive_observation(scenario: Scenario, adapter: str) -> RawObservation:
    return _surface(
        scenario.nuisance_seed,
        scenario.scenario_id,
        "passive",
        adapter,
        passive_success(scenario.faults),
    )


def ledger_probe(scenario: Scenario, probe_id: str) -> RawObservation:
    probe = PROBE_BY_ID[probe_id]
    ledger = [relation for relation in RELATIONS if relation in scenario.faults]
    remaining = [relation for relation in ledger if relation not in probe.repairs]
    success = len(remaining) == 0
    return _surface(scenario.nuisance_seed, scenario.scenario_id, probe_id, "ledger-v3", success)


def queue_probe(scenario: Scenario, probe_id: str) -> RawObservation:
    probe = PROBE_BY_ID[probe_id]
    queue = list(scenario.faults)
    remaining: list[str] = []
    while queue:
        relation = queue.pop(0)
        if relation not in probe.repairs:
            remaining.append(relation)
    success = not remaining
    return _surface(scenario.nuisance_seed, scenario.scenario_id, probe_id, "queue-v3", success)


def query_fn(scenario: Scenario, adapter: str):
    if adapter == "ledger-v3":
        return lambda probe_id: ledger_probe(scenario, probe_id)
    if adapter == "queue-v3":
        return lambda probe_id: queue_probe(scenario, probe_id)
    raise ValueError(f"unknown adapter: {adapter}")


def evaluation_scenarios(identities: int = 16) -> tuple[Scenario, ...]:
    rows: list[Scenario] = []
    for family_index, faults in enumerate(EVALUATION_FAULTS):
        for identity in range(identities):
            rows.append(
                Scenario(
                    scenario_id=f"eval-{family_index:02d}-{identity:02d}",
                    faults=faults,
                    nuisance_seed=1000 + family_index * 97 + identity * 13,
                )
            )
    return tuple(rows)
