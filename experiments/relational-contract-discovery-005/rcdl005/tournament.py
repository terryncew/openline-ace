"""Run the frozen equal-budget causal-utility tournament."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Callable

from .canonical import canonical_digest
from .domain import (
    ACTION_IDS,
    FINAL_SCENARIOS,
    HYPOTHESES,
    IMPLEMENTATIONS,
    ONLINE_BUDGET,
    RELATIONS,
    Scenario,
    behavior_preserved,
    class_members,
    final_scenarios,
    minimal_failure_sets,
    signature_for_class,
    verify_domain,
)
from .execution import execute_pair, execute_recovery
from .policies import (
    ActivePolicy,
    PolicyOutput,
    make_learned_policy,
    make_symbolic_policy,
    policy_boundary,
)


@dataclass(frozen=True)
class RunResult:
    scenario_id: str
    observable_class: str
    hypothesis_id: str
    implementation: str
    policy: str
    output: PolicyOutput
    expected_signature: tuple[bool, ...]
    correct_contract: bool
    correct_structural_status: bool
    recovery_attempts: int
    immediate_recoveries: int
    eventual_recoveries: int
    sham_failures: int
    query_trace_digests: tuple[tuple[str, str], ...]
    recovery_choices: tuple[tuple[str, str, bool, int], ...]

    @property
    def explanation(self) -> tuple[tuple[str, ...], ...] | None:
        return None if self.output.signature is None else minimal_failure_sets(self.output.signature)

    def to_record(self) -> dict[str, Any]:
        return {
            "schema": "rcdl.causal-utility-result/0.5",
            "scenario_id": self.scenario_id,
            "observable_class": self.observable_class,
            "hypothesis_id": self.hypothesis_id,
            "implementation": self.implementation,
            "policy": self.policy,
            "queries": list(self.output.queries),
            "query_count": len(self.output.queries),
            "candidate_id": self.output.candidate_id,
            "predicted_signature": None
            if self.output.signature is None
            else list(self.output.signature),
            "expected_signature": list(self.expected_signature),
            "minimal_failure_sets": None
            if self.explanation is None
            else [list(item) for item in self.explanation],
            "structural_status": self.output.structural_status,
            "structural_multiplicity": self.output.structural_multiplicity,
            "correct_contract": self.correct_contract,
            "correct_structural_status": self.correct_structural_status,
            "recovery_attempts": self.recovery_attempts,
            "immediate_recoveries": self.immediate_recoveries,
            "eventual_recoveries": self.eventual_recoveries,
            "sham_failures": self.sham_failures,
            "query_trace_digests": [list(item) for item in self.query_trace_digests],
            "recovery_choices": [list(item) for item in self.recovery_choices],
        }


def verify_exhaustive_oracle() -> dict[str, Any]:
    break_sets = tuple(
        frozenset(group)
        for size in range(len(RELATIONS) + 1)
        for group in combinations(RELATIONS, size)
    )
    table: dict[str, tuple[bool, ...]] = {}
    for hypothesis in HYPOTHESES:
        outcomes = tuple(
            behavior_preserved(hypothesis.family, broken) for broken in break_sets
        )
        if not outcomes[0]:
            raise RuntimeError("oracle fails at baseline")
        table[hypothesis.id] = outcomes
    ambiguous = class_members("class-03")
    left, right = (table[item] for item in ambiguous)
    declared_indexes = [
        index for index, broken in enumerate(break_sets) if 1 <= len(broken) <= 2
    ]
    outside_indexes = [index for index, broken in enumerate(break_sets) if len(broken) > 2]
    if any(left[index] != right[index] for index in declared_indexes):
        raise RuntimeError("declared non-identifiable class is distinguishable in regime")
    if not any(left[index] != right[index] for index in outside_indexes):
        raise RuntimeError("non-identifiable controls are globally identical")
    return {
        "valid": True,
        "hypotheses": len(HYPOTHESES),
        "states_per_hypothesis": len(break_sets),
        "oracle_comparisons": len(HYPOTHESES) * len(break_sets),
        "declared_action_count": len(ACTION_IDS),
        "non_identifiable_class": "class-03",
        "indistinguishable_within_regime": True,
        "distinguishable_outside_regime": True,
    }


def _run_policy(
    scenario: Scenario,
    implementation: str,
    factory: Callable[[], ActivePolicy],
) -> RunResult:
    policy = factory()
    trace_digests: list[tuple[str, str]] = []
    recovery_choices: list[tuple[str, str, bool, int]] = []
    recovery_attempts = 0
    immediate_recoveries = 0
    eventual_recoveries = 0
    sham_failures = 0
    for _ in range(ONLINE_BUDGET):
        action_id = policy.choose_action()
        if action_id is None:
            break
        pair = execute_pair(scenario, action_id, implementation)
        trace_digests.append((pair.active.digest, pair.sham.digest))
        sham_failures += int(pair.sham_outcome.failed)
        policy.observe(
            action_id,
            pair.active_outcome.failed,
            pair.sham_outcome.failed,
        )
        if pair.active_outcome.failed:
            recovery_attempts += 1
            restored = policy.recommend_recovery(action_id)
            recovery = execute_recovery(scenario, action_id, restored)
            immediate_recoveries += int(recovery.immediate_preservation)
            eventual_recoveries += int(recovery.eventual_preservation)
            recovery_choices.append(
                (
                    action_id,
                    restored,
                    recovery.immediate_preservation,
                    recovery.horizon,
                )
            )
    output = policy.finish()
    expected = signature_for_class(scenario.observable_class)
    expected_status = (
        "NON_IDENTIFIABLE"
        if len(class_members(scenario.observable_class)) > 1
        else "IDENTIFIED"
    )
    return RunResult(
        scenario.id,
        scenario.observable_class,
        scenario.hypothesis_id,
        implementation,
        policy.name,
        output,
        expected,
        output.signature == expected,
        output.structural_status == expected_status,
        recovery_attempts,
        immediate_recoveries,
        eventual_recoveries,
        sham_failures,
        tuple(trace_digests),
        tuple(recovery_choices),
    )


def _transport_ok(rows: tuple[RunResult, ...]) -> bool:
    grouped: dict[tuple[str, str], list[RunResult]] = {}
    for row in rows:
        grouped.setdefault((row.scenario_id, row.policy), []).append(row)
    if any({item.implementation for item in group} != set(IMPLEMENTATIONS) for group in grouped.values()):
        return False
    return all(
        len(
            {
                (
                    item.output.signature,
                    item.output.structural_status,
                    item.output.queries,
                    item.recovery_choices,
                    item.explanation,
                )
                for item in group
            }
        )
        == 1
        for group in grouped.values()
    )


def _nuisance_ok(rows: tuple[RunResult, ...]) -> bool:
    grouped: dict[tuple[str, str, str], list[RunResult]] = {}
    for row in rows:
        grouped.setdefault((row.observable_class, row.implementation, row.policy), []).append(row)
    return all(
        len(
            {
                (
                    item.output.signature,
                    item.output.structural_status,
                    item.output.queries,
                    item.explanation,
                )
                for item in group
            }
        )
        == 1
        for group in grouped.values()
    )


def _metrics(name: str, rows: tuple[RunResult, ...]) -> dict[str, Any]:
    selected = tuple(row for row in rows if row.policy == name)
    attempts = sum(row.recovery_attempts for row in selected)
    return {
        "policy": name,
        "implementation_runs": len(selected),
        "correct_contracts": sum(row.correct_contract for row in selected),
        "contract_accuracy_ppm": sum(row.correct_contract for row in selected) * 1_000_000 // len(selected),
        "correct_structural_status": sum(row.correct_structural_status for row in selected),
        "structural_status_accuracy_ppm": sum(row.correct_structural_status for row in selected) * 1_000_000 // len(selected),
        "total_queries": sum(len(row.output.queries) for row in selected),
        "mean_queries_milli": sum(len(row.output.queries) for row in selected) * 1_000 // len(selected),
        "recovery_attempts": attempts,
        "immediate_recoveries": sum(row.immediate_recoveries for row in selected),
        "immediate_recovery_accuracy_ppm": 1_000_000
        if not attempts
        else sum(row.immediate_recoveries for row in selected) * 1_000_000 // attempts,
        "eventual_recoveries": sum(row.eventual_recoveries for row in selected),
        "sham_failures": sum(row.sham_failures for row in selected),
    }


def _verdict(metrics: tuple[dict[str, Any], ...], valid: bool) -> str:
    if not valid:
        return "INVALID_TOURNAMENT"
    symbolic = next(item for item in metrics if item["policy"] == "rcdl_symbolic_version_space")
    learned = next(item for item in metrics if item["policy"] == "learned_intervention_signature")
    primary_symbolic = (
        symbolic["correct_contracts"],
        symbolic["correct_structural_status"],
        symbolic["immediate_recoveries"],
        -symbolic["total_queries"],
    )
    primary_learned = (
        learned["correct_contracts"],
        learned["correct_structural_status"],
        learned["immediate_recoveries"],
        -learned["total_queries"],
    )
    if primary_symbolic == primary_learned:
        return "CAUSAL_UTILITY_PARITY"
    if all(left >= right for left, right in zip(primary_symbolic, primary_learned, strict=True)):
        return "RCDL_STRICT_UTILITY_WIN"
    if all(left <= right for left, right in zip(primary_symbolic, primary_learned, strict=True)):
        return "LEARNED_STRICT_UTILITY_WIN"
    return "MIXED_CAUSAL_UTILITY"


def run_tournament() -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    domain = verify_domain()
    oracle = verify_exhaustive_oracle()
    boundary = policy_boundary()
    scenarios = final_scenarios()
    if len(scenarios) != FINAL_SCENARIOS:
        raise RuntimeError("final audit scenario closure failed")
    rows: list[RunResult] = []
    factories = (make_symbolic_policy, make_learned_policy)
    for scenario in scenarios:
        for implementation in IMPLEMENTATIONS:
            for factory in factories:
                rows.append(_run_policy(scenario, implementation, factory))
    materialized = tuple(rows)
    names = tuple(sorted({row.policy for row in materialized}))
    metrics = tuple(_metrics(name, materialized) for name in names)
    transport = _transport_ok(materialized)
    nuisance = _nuisance_ok(materialized)
    all_resolved = all(row.output.signature is not None for row in materialized)
    no_sham_failures = all(row.sham_failures == 0 for row in materialized)
    within_budget = all(len(row.output.queries) <= ONLINE_BUDGET for row in materialized)
    valid = bool(
        domain["valid"]
        and oracle["valid"]
        and boundary["valid"]
        and transport
        and nuisance
        and all_resolved
        and no_sham_failures
        and within_budget
    )
    verdict = _verdict(metrics, valid)
    records = tuple(row.to_record() for row in materialized)
    result = {
        "schema": "rcdl.causal-utility-tournament/0.5",
        "question": "Does symbolic RCDL retain causal selection, recovery, or explanation utility over a learned intervention-signature policy under equal information and action budgets?",
        "protocol_status": "VALID_RESULT" if valid else "INVALID_RESULT",
        "scientific_verdict": verdict,
        "domain": domain,
        "oracle": oracle,
        "policy_boundary": boundary,
        "protocol": {
            "final_scenarios": FINAL_SCENARIOS,
            "implementations": list(IMPLEMENTATIONS),
            "policy_count": len(factories),
            "implementation_runs": len(materialized),
            "online_budget": ONLINE_BUDGET,
            "matched_sham_per_query": True,
            "development_contexts_excluded_from_final_scenarios": True,
            "same_builder": True,
            "independent_replication": False,
        },
        "checks": {
            "transport_across_implementations": transport,
            "nuisance_stability": nuisance,
            "all_outputs_resolved": all_resolved,
            "no_sham_failures": no_sham_failures,
            "within_online_budget": within_budget,
        },
        "metrics": list(metrics),
        "record_count": len(records),
        "record_digest": canonical_digest(records),
        "class_counts": dict(sorted(Counter(row.observable_class for row in materialized).items())),
    }
    return result, records

