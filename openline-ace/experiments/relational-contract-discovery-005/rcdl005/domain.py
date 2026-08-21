"""Frozen contract grammar, scenarios, and exhaustive behavioral oracle."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from .canonical import canonical_digest

RELATIONS = ("provenance", "review", "ordering", "fresh_state")
IMPLEMENTATIONS = ("ledger", "queue")
ONLINE_BUDGET = 4
FINAL_SCENARIOS = 256


def _contract(*members: str) -> frozenset[str]:
    value = frozenset(members)
    if not value or not value <= set(RELATIONS):
        raise ValueError("contract contains an invalid relation")
    return value


def _family(*contracts: frozenset[str]) -> tuple[frozenset[str], ...]:
    ordered = tuple(sorted(contracts, key=lambda item: (len(item), tuple(sorted(item)))))
    if not ordered or len(set(ordered)) != len(ordered):
        raise ValueError("contract family must be non-empty and unique")
    if any(left < right or right < left for left, right in combinations(ordered, 2)):
        raise ValueError("contract family must be an inclusion antichain")
    return ordered


@dataclass(frozen=True)
class Hypothesis:
    id: str
    observable_class: str
    family: tuple[frozenset[str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "observable_class": self.observable_class,
            "family": [sorted(contract) for contract in self.family],
        }


HYPOTHESES = (
    Hypothesis("single_provenance", "class-01", _family(_contract("provenance"))),
    Hypothesis(
        "provenance_and_review",
        "class-02",
        _family(_contract("provenance", "review")),
    ),
    Hypothesis(
        "provenance_or_review",
        "class-03",
        _family(_contract("provenance"), _contract("review")),
    ),
    Hypothesis(
        "review_or_provenance_ordering_with_fresh_anchor",
        "class-03",
        _family(
            _contract("review"),
            _contract("provenance", "ordering"),
            _contract("provenance", "fresh_state"),
        ),
    ),
    Hypothesis(
        "ordering_anchor_with_provenance_review_substitutes",
        "class-04",
        _family(
            _contract("provenance", "ordering"),
            _contract("review", "ordering"),
        ),
    ),
    Hypothesis(
        "disjoint_pair_substitutes",
        "class-05",
        _family(
            _contract("provenance", "review"),
            _contract("ordering", "fresh_state"),
        ),
    ),
    Hypothesis(
        "two_substitution_groups",
        "class-06",
        _family(
            _contract("provenance", "ordering"),
            _contract("provenance", "fresh_state"),
            _contract("review", "ordering"),
            _contract("review", "fresh_state"),
        ),
    ),
    Hypothesis(
        "fresh_anchor_with_three_substitutes",
        "class-07",
        _family(
            _contract("provenance", "fresh_state"),
            _contract("review", "fresh_state"),
            _contract("ordering", "fresh_state"),
        ),
    ),
    Hypothesis(
        "provenance_or_review_ordering_pair",
        "class-08",
        _family(_contract("provenance"), _contract("review", "ordering")),
    ),
)

HYPOTHESIS_BY_ID = {item.id: item for item in HYPOTHESES}
OBSERVABLE_CLASSES = tuple(sorted({item.observable_class for item in HYPOTHESES}))


def _actions() -> tuple[frozenset[str], ...]:
    return tuple(
        frozenset(group)
        for size in (1, 2)
        for group in combinations(RELATIONS, size)
    )


ACTIONS = _actions()
ACTION_IDS = tuple("break:" + "+".join(sorted(action)) for action in ACTIONS)
ACTION_BY_ID = dict(zip(ACTION_IDS, ACTIONS, strict=True))


def behavior_preserved(
    family: tuple[frozenset[str], ...], broken: Iterable[str]
) -> bool:
    broken_set = frozenset(broken)
    if not broken_set <= set(RELATIONS):
        raise ValueError("broken set contains an invalid relation")
    return any(contract.isdisjoint(broken_set) for contract in family)


def failed(family: tuple[frozenset[str], ...], broken: Iterable[str]) -> bool:
    return not behavior_preserved(family, broken)


def signature(hypothesis: Hypothesis) -> tuple[bool, ...]:
    return tuple(failed(hypothesis.family, action) for action in ACTIONS)


def signature_for_class(class_id: str) -> tuple[bool, ...]:
    members = tuple(item for item in HYPOTHESES if item.observable_class == class_id)
    if not members:
        raise ValueError(f"unknown observable class: {class_id}")
    signatures = {signature(item) for item in members}
    if len(signatures) != 1:
        raise RuntimeError("observable class contains distinguishable hypotheses")
    return signatures.pop()


def minimal_failure_sets(outcome_signature: tuple[bool, ...]) -> tuple[tuple[str, ...], ...]:
    if len(outcome_signature) != len(ACTIONS):
        raise ValueError("signature length mismatch")
    failures = [action for action, outcome in zip(ACTIONS, outcome_signature, strict=True) if outcome]
    minimal = [
        action
        for action in failures
        if not any(other < action for other in failures)
    ]
    return tuple(tuple(sorted(action)) for action in sorted(minimal, key=lambda x: (len(x), tuple(sorted(x)))))


def class_members(class_id: str) -> tuple[str, ...]:
    members = tuple(sorted(item.id for item in HYPOTHESES if item.observable_class == class_id))
    if not members:
        raise ValueError(f"unknown observable class: {class_id}")
    return members


@dataclass(frozen=True)
class Scenario:
    id: str
    ordinal: int
    hypothesis_id: str
    observable_class: str
    nuisance_seed: int

    @property
    def hypothesis(self) -> Hypothesis:
        return HYPOTHESIS_BY_ID[self.hypothesis_id]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "ordinal": self.ordinal,
            "hypothesis_id": self.hypothesis_id,
            "observable_class": self.observable_class,
            "nuisance_seed": self.nuisance_seed,
        }


def final_scenarios() -> tuple[Scenario, ...]:
    """Return 32 scenarios per observable class; class-03 alternates its twins."""

    rows: list[Scenario] = []
    by_class = {
        class_id: tuple(item for item in HYPOTHESES if item.observable_class == class_id)
        for class_id in OBSERVABLE_CLASSES
    }
    ordinal = 0
    for class_id in OBSERVABLE_CLASSES:
        members = by_class[class_id]
        for within_class in range(32):
            hypothesis = members[within_class % len(members)]
            seed = 50_000 + ordinal * 7_919
            identity = canonical_digest(
                {
                    "split": "final-audit",
                    "ordinal": ordinal,
                    "hypothesis": hypothesis.id,
                    "seed": seed,
                }
            )
            rows.append(Scenario(identity, ordinal, hypothesis.id, class_id, seed))
            ordinal += 1
    if len(rows) != FINAL_SCENARIOS:
        raise RuntimeError("final scenario count changed")
    return tuple(rows)


def verify_domain() -> dict[str, object]:
    if len(HYPOTHESIS_BY_ID) != len(HYPOTHESES):
        raise RuntimeError("duplicate hypothesis id")
    if OBSERVABLE_CLASSES != tuple(f"class-{index:02d}" for index in range(1, 9)):
        raise RuntimeError("observable-class closure changed")
    signatures = {class_id: signature_for_class(class_id) for class_id in OBSERVABLE_CLASSES}
    if len(set(signatures.values())) != len(signatures):
        raise RuntimeError("different observable classes share a signature")
    if len(ACTIONS) != 10 or len(set(ACTION_IDS)) != 10:
        raise RuntimeError("action vocabulary changed")
    scenarios = final_scenarios()
    counts = {class_id: sum(row.observable_class == class_id for row in scenarios) for class_id in OBSERVABLE_CLASSES}
    if set(counts.values()) != {32}:
        raise RuntimeError("final scenarios are not class balanced")
    return {
        "valid": True,
        "relations": len(RELATIONS),
        "actions": len(ACTIONS),
        "hypotheses": len(HYPOTHESES),
        "observable_classes": len(OBSERVABLE_CLASSES),
        "non_identifiable_classes": [
            class_id for class_id in OBSERVABLE_CLASSES if len(class_members(class_id)) > 1
        ],
        "final_scenarios": len(scenarios),
    }

