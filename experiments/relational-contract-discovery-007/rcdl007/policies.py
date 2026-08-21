from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .arena import DEVELOPMENT_FAULTS, PROBES, passive_success, predicted_success, standing_for_faults
from .model import PolicyDecision, QueryEvent, QueryFn, RawObservation, Standing


BUDGET = 4
ALL_HYPOTHESES = tuple(
    frozenset(items)
    for mask in range(1 << 4)
    for items in [
        tuple(relation for bit, relation in enumerate(("freshness", "lineage", "submit_gate", "timeout_gate")) if mask & (1 << bit))
    ]
)


def _choice_score(groups: dict[bool, list[object]], standing_of) -> tuple[int, int, int]:
    nonempty = [group for group in groups.values() if group]
    worst_standing_count = max(len({standing_of(item) for item in group}) for group in nonempty)
    worst_size = max(len(group) for group in nonempty)
    imbalance = abs(len(groups[True]) - len(groups[False]))
    return worst_standing_count, worst_size, imbalance


def _all_same_standing(items, standing_of):
    standings = {standing_of(item) for item in items}
    return next(iter(standings)) if len(standings) == 1 else None


def symbolic_decide(passive: RawObservation, query: QueryFn, budget: int = BUDGET) -> PolicyDecision:
    candidates = [hyp for hyp in ALL_HYPOTHESES if passive_success(hyp) == passive.external_success]
    queries: list[QueryEvent] = []
    resolved = _all_same_standing(candidates, standing_for_faults)
    if resolved is not None:
        return PolicyDecision(resolved, tuple(queries), "SYMBOLIC_PASSIVE_RESOLUTION")

    for _ in range(budget):
        best = None
        queried_ids = {event.probe_id for event in queries}
        for probe in PROBES:
            if probe.probe_id in queried_ids:
                continue
            groups = {True: [], False: []}
            for hyp in candidates:
                groups[predicted_success(hyp, probe.repairs)].append(hyp)
            score = _choice_score(groups, standing_for_faults) + (probe.probe_id,)
            if best is None or score < best[0]:
                best = (score, probe)
        if best is None:
            break
        probe = best[1]
        observation = query(probe.probe_id)
        queries.append(QueryEvent(probe.probe_id, observation))
        candidates = [
            hyp for hyp in candidates if predicted_success(hyp, probe.repairs) == observation.external_success
        ]
        if not candidates:
            return PolicyDecision(Standing.INVALID, tuple(queries), "SYMBOLIC_EMPTY_VERSION_SPACE")
        resolved = _all_same_standing(candidates, standing_for_faults)
        if resolved is not None:
            return PolicyDecision(resolved, tuple(queries), "SYMBOLIC_VERSION_SPACE_RESOLUTION")

    counts = Counter(standing_for_faults(hyp) for hyp in candidates)
    if not counts:
        return PolicyDecision(Standing.INVALID, tuple(queries), "SYMBOLIC_NO_CANDIDATE")
    standing = sorted(counts.items(), key=lambda item: (-item[1], item[0].value))[0][0]
    return PolicyDecision(standing, tuple(queries), "SYMBOLIC_BUDGET_MAJORITY")


@dataclass(frozen=True)
class LearnedRecord:
    record_id: str
    passive_success: bool
    responses: dict[str, bool]
    standing: Standing


@dataclass(frozen=True)
class LearnedActivePolicy:
    records: tuple[LearnedRecord, ...]

    def decide(self, passive: RawObservation, query: QueryFn, budget: int = BUDGET) -> PolicyDecision:
        history: list[QueryEvent] = []

        def mismatch(record: LearnedRecord) -> int:
            total = int(record.passive_success != passive.external_success)
            total += sum(
                int(record.responses[event.probe_id] != event.observation.external_success)
                for event in history
            )
            return total

        for _ in range(budget + 1):
            minimum = min(mismatch(record) for record in self.records)
            nearest = [record for record in self.records if mismatch(record) == minimum]
            resolved = _all_same_standing(nearest, lambda record: record.standing)
            if resolved is not None:
                return PolicyDecision(resolved, tuple(history), "LEARNED_NEAREST_SIGNATURE_RESOLUTION")
            if len(history) >= budget:
                counts = Counter(record.standing for record in nearest)
                standing = sorted(counts.items(), key=lambda item: (-item[1], item[0].value))[0][0]
                return PolicyDecision(standing, tuple(history), "LEARNED_BUDGET_MAJORITY")

            best = None
            queried_ids = {event.probe_id for event in history}
            for probe in PROBES:
                if probe.probe_id in queried_ids:
                    continue
                groups = {True: [], False: []}
                for record in nearest:
                    groups[record.responses[probe.probe_id]].append(record)
                score = _choice_score(groups, lambda record: record.standing) + (probe.probe_id,)
                if best is None or score < best[0]:
                    best = (score, probe)
            if best is None:
                return PolicyDecision(Standing.INVALID, tuple(history), "LEARNED_NO_PROBE")
            probe = best[1]
            history.append(QueryEvent(probe.probe_id, query(probe.probe_id)))

        return PolicyDecision(Standing.INVALID, tuple(history), "LEARNED_UNREACHABLE")


def train_learned_policy() -> LearnedActivePolicy:
    records: list[LearnedRecord] = []
    for index, faults in enumerate(DEVELOPMENT_FAULTS):
        records.append(
            LearnedRecord(
                record_id=f"dev-{index:02d}",
                passive_success=passive_success(faults),
                responses={probe.probe_id: predicted_success(faults, probe.repairs) for probe in PROBES},
                standing=standing_for_faults(faults),
            )
        )
    return LearnedActivePolicy(tuple(records))


def policy_boundary() -> dict[str, object]:
    return {
        "budget": BUDGET,
        "shared_public_inputs": [
            "passive RawObservation",
            "opaque probe IDs",
            "RawObservation returned by selected probes",
        ],
        "forbidden_eval_inputs": [
            "artifact_valid",
            "fault set",
            "standing label",
            "recovery horizon",
            "relation names",
            "verdict-derived features",
        ],
        "learned_history": "action-complete development response signatures with training standings",
        "shared_probe_selector": "deterministic minimax partition",
        "policy_authority": "NONE",
    }
