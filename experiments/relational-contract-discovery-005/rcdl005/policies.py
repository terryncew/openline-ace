"""Equal-budget symbolic and learned active intervention policies."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .canonical import canonical_digest, canonical_json, load_json_bytes
from .domain import (
    ACTION_BY_ID,
    ACTION_IDS,
    HYPOTHESES,
    OBSERVABLE_CLASSES,
    class_members,
    signature_for_class,
)

HISTORICAL_PATH = Path(__file__).resolve().parents[1] / "references" / "frozen-historical-interventions.json"


@dataclass(frozen=True)
class Candidate:
    id: str
    signature: tuple[bool, ...]
    structural_multiplicity: int
    members: tuple[str, ...]

    def outcome(self, action_id: str) -> bool:
        return self.signature[ACTION_IDS.index(action_id)]


@dataclass(frozen=True)
class PolicyOutput:
    policy: str
    candidate_id: str | None
    signature: tuple[bool, ...] | None
    structural_status: str
    structural_multiplicity: int
    members: tuple[str, ...]
    queries: tuple[str, ...]


def load_historical_interventions(path: Path = HISTORICAL_PATH) -> tuple[dict[str, object], ...]:
    payload = path.read_bytes()
    document = load_json_bytes(payload)
    if not isinstance(document, dict) or payload != canonical_json(document) + b"\n":
        raise ValueError("historical intervention corpus is not canonical")
    if set(document) != {"schema", "information_boundary", "records"}:
        raise ValueError("historical intervention corpus closure failed")
    if document["schema"] != "rcdl.historical-interventions/0.5":
        raise ValueError("unsupported historical intervention schema")
    if document["information_boundary"] != {
        "final_scenario_ids_available": False,
        "hypothesis_ids_available": False,
        "observable_class_labels_available": False,
        "one_context_per_candidate_mechanism": True,
        "action_ids_available": True,
        "active_outcomes_available": True,
        "sham_outcomes_available": True,
    }:
        raise ValueError("historical information boundary changed")
    records = document["records"]
    if not isinstance(records, list):
        raise ValueError("historical records must be a list")
    expected_keys = {"context_id", "action_id", "active_failed", "sham_failed"}
    parsed: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != expected_keys:
            raise ValueError("historical record closure failed")
        context = record["context_id"]
        action = record["action_id"]
        if (
            not isinstance(context, str)
            or len(context) != 64
            or action not in ACTION_BY_ID
            or not isinstance(record["active_failed"], bool)
            or record["sham_failed"] is not False
            or (context, str(action)) in seen
        ):
            raise ValueError("historical record value failed")
        seen.add((context, str(action)))
        parsed.append(record)
    contexts = {str(record["context_id"]) for record in parsed}
    if len(contexts) != len(HYPOTHESES) or len(parsed) != len(HYPOTHESES) * len(ACTION_IDS):
        raise ValueError("historical corpus cardinality failed")
    for context in contexts:
        if {record["action_id"] for record in parsed if record["context_id"] == context} != set(ACTION_IDS):
            raise ValueError("historical context is not action-complete")
    return tuple(parsed)


def symbolic_candidates() -> tuple[Candidate, ...]:
    return tuple(
        Candidate(
            class_id,
            signature_for_class(class_id),
            len(class_members(class_id)),
            class_members(class_id),
        )
        for class_id in OBSERVABLE_CLASSES
    )


def learned_candidates(
    records: Iterable[dict[str, object]],
) -> tuple[Candidate, ...]:
    materialized = tuple(records)
    if not materialized:
        raise ValueError("learned policy requires historical interventions")
    if any(
        set(record) != {"context_id", "action_id", "active_failed", "sham_failed"}
        or record.get("action_id") not in ACTION_BY_ID
        or not isinstance(record.get("active_failed"), bool)
        or record.get("sham_failed") is not False
        for record in materialized
    ):
        raise ValueError("learned historical intervention boundary failed")
    contexts = sorted({str(record["context_id"]) for record in materialized})
    if any(
        {str(record["action_id"]) for record in materialized if str(record["context_id"]) == context}
        != set(ACTION_IDS)
        for context in contexts
    ):
        raise ValueError("learned historical context is not action-complete")
    by_signature: dict[tuple[bool, ...], list[str]] = {}
    for context in contexts:
        outcomes = {
            str(record["action_id"]): bool(record["active_failed"])
            for record in materialized
            if record["context_id"] == context
        }
        signature = tuple(outcomes[action_id] for action_id in ACTION_IDS)
        by_signature.setdefault(signature, []).append(context)
    return tuple(
        Candidate(
            "learned-" + canonical_digest(list(signature))[:16],
            signature,
            len(contexts_for_signature),
            tuple(sorted(contexts_for_signature)),
        )
        for signature, contexts_for_signature in sorted(
            by_signature.items(), key=lambda item: canonical_digest(list(item[0]))
        )
    )


class ActivePolicy:
    def __init__(self, name: str, candidates: Iterable[Candidate]) -> None:
        self.name = name
        self._initial = tuple(candidates)
        if len(self._initial) < 2 or len({item.signature for item in self._initial}) != len(self._initial):
            raise ValueError("policy candidates must contain unique signatures")
        self.reset()

    def reset(self) -> None:
        self.remaining = self._initial
        self.queries: list[str] = []

    def choose_action(self) -> str | None:
        if len(self.remaining) <= 1:
            return None
        available = [action_id for action_id in ACTION_IDS if action_id not in self.queries]
        scored: list[tuple[int, int, int, str]] = []
        for action_id in available:
            failures = sum(candidate.outcome(action_id) for candidate in self.remaining)
            preserved = len(self.remaining) - failures
            if not failures or not preserved:
                continue
            scored.append(
                (
                    max(failures, preserved),
                    abs(failures - preserved),
                    len(ACTION_BY_ID[action_id]),
                    action_id,
                )
            )
        if not scored:
            return None
        return min(scored)[-1]

    def observe(self, action_id: str, active_failed: bool, sham_failed: bool) -> None:
        if action_id not in ACTION_BY_ID or action_id in self.queries:
            raise ValueError("policy received an invalid or repeated action")
        if sham_failed:
            raise ValueError("sham failure invalidates the intervention")
        self.queries.append(action_id)
        self.remaining = tuple(
            candidate for candidate in self.remaining if candidate.outcome(action_id) == active_failed
        )
        if not self.remaining:
            raise ValueError("observation eliminated the complete policy version space")

    def recommend_recovery(self, action_id: str) -> str:
        broken = ACTION_BY_ID[action_id]
        if not broken:
            raise ValueError("cannot recover an empty intervention")
        scored: list[tuple[int, str]] = []
        for restored in sorted(broken):
            remaining_broken = broken - {restored}
            if not remaining_broken:
                predicted_failures = 0
            else:
                reduced_action = "break:" + "+".join(sorted(remaining_broken))
                predicted_failures = sum(
                    candidate.outcome(reduced_action) for candidate in self.remaining
                )
            scored.append((predicted_failures, restored))
        return min(scored)[1]

    def finish(self) -> PolicyOutput:
        if len(self.remaining) != 1:
            return PolicyOutput(
                self.name,
                None,
                None,
                "UNRESOLVED",
                0,
                (),
                tuple(self.queries),
            )
        candidate = self.remaining[0]
        status = "NON_IDENTIFIABLE" if candidate.structural_multiplicity > 1 else "IDENTIFIED"
        return PolicyOutput(
            self.name,
            candidate.id,
            candidate.signature,
            status,
            candidate.structural_multiplicity,
            candidate.members,
            tuple(self.queries),
        )


def make_symbolic_policy() -> ActivePolicy:
    return ActivePolicy("rcdl_symbolic_version_space", symbolic_candidates())


def make_learned_policy(records: Iterable[dict[str, object]] | None = None) -> ActivePolicy:
    corpus = load_historical_interventions() if records is None else tuple(records)
    return ActivePolicy("learned_intervention_signature", learned_candidates(corpus))


def policy_boundary() -> dict[str, object]:
    records = load_historical_interventions()
    symbolic = symbolic_candidates()
    learned = learned_candidates(records)
    if {item.signature for item in symbolic} != {item.signature for item in learned}:
        raise RuntimeError("symbolic and learned policies do not start with equal outcome support")
    return {
        "valid": True,
        "same_action_vocabulary": True,
        "same_historical_interventions_available": True,
        "same_online_budget": True,
        "same_outcome_support": True,
        "symbolic_candidate_count": len(symbolic),
        "learned_candidate_count": len(learned),
        "historical_record_count": len(records),
        "difference": "symbolic contract grammar versus learned intervention signatures",
    }
