from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict

from .arena import evaluation_scenarios, passive_observation, query_fn, standing_for_faults
from .model import PolicyDecision
from .policies import BUDGET, symbolic_decide, train_learned_policy


ADAPTERS = ("ledger-v3", "queue-v3")
POLICIES = ("symbolic", "learned")


def _decision_row(scenario, adapter: str, policy_name: str, decision: PolicyDecision) -> dict[str, object]:
    expected = standing_for_faults(scenario.faults)
    return {
        "adapter": adapter,
        "correct": decision.standing == expected,
        "expected_standing": expected.value,
        "explanation_code": decision.explanation_code,
        "policy": policy_name,
        "predicted_standing": decision.standing.value,
        "probe_ids": [event.probe_id for event in decision.queries],
        "query_count": len(decision.queries),
        "scenario_id": scenario.scenario_id,
    }


def run_tournament(identities: int = 16) -> dict[str, object]:
    learned = train_learned_policy()
    rows: list[dict[str, object]] = []
    for scenario in evaluation_scenarios(identities):
        for adapter in ADAPTERS:
            passive = passive_observation(scenario, adapter)
            symbolic = symbolic_decide(passive, query_fn(scenario, adapter))
            learned_decision = learned.decide(passive, query_fn(scenario, adapter))
            rows.append(_decision_row(scenario, adapter, "symbolic", symbolic))
            rows.append(_decision_row(scenario, adapter, "learned", learned_decision))

    expected_rows = len(evaluation_scenarios(identities)) * len(ADAPTERS) * len(POLICIES)
    if len(rows) != expected_rows:
        raise RuntimeError("row-count boundary failed")
    if any(int(row["query_count"]) > BUDGET for row in rows):
        raise RuntimeError("query-budget boundary failed")

    by_policy: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_policy[str(row["policy"])].append(row)

    metrics: dict[str, dict[str, object]] = {}
    for policy_name, policy_rows in by_policy.items():
        correct = sum(bool(row["correct"]) for row in policy_rows)
        query_total = sum(int(row["query_count"]) for row in policy_rows)
        metrics[policy_name] = {
            "accuracy_ppm": round(correct * 1_000_000 / len(policy_rows)),
            "correct": correct,
            "query_total": query_total,
            "records": len(policy_rows),
            "mean_queries": query_total / len(policy_rows),
            "max_queries": max(int(row["query_count"]) for row in policy_rows),
        }

    transport_failures = 0
    for scenario in evaluation_scenarios(identities):
        for policy_name in POLICIES:
            selected = [
                row for row in rows if row["scenario_id"] == scenario.scenario_id and row["policy"] == policy_name
            ]
            signatures = {(row["predicted_standing"], tuple(row["probe_ids"])) for row in selected}
            if len(signatures) != 1:
                transport_failures += 1

    symbolic = metrics["symbolic"]
    learned_metric = metrics["learned"]
    symbolic_accuracy = int(symbolic["accuracy_ppm"])
    learned_accuracy = int(learned_metric["accuracy_ppm"])
    symbolic_queries = int(symbolic["query_total"])
    learned_queries = int(learned_metric["query_total"])

    if transport_failures:
        verdict = "INVALID_TRANSPORT_FAILURE"
    elif symbolic_accuracy < learned_accuracy:
        verdict = "LEARNED_PRE_ADJUDICATION_ADVANTAGE"
    elif symbolic_accuracy > learned_accuracy:
        verdict = "SYMBOLIC_PRE_ADJUDICATION_ACCURACY_ADVANTAGE"
    elif learned_queries > 0 and symbolic_queries * 5 <= learned_queries * 4:
        verdict = "SYMBOLIC_QUERY_EFFICIENCY_ADVANTAGE"
    elif symbolic_queries == learned_queries:
        verdict = "PRE_ADJUDICATION_CAUSAL_PARITY"
    else:
        verdict = "PRE_ADJUDICATION_NO_UNIQUE_ADVANTAGE"

    return {
        "authority": "NONE",
        "budget": BUDGET,
        "claim_effect": (
            "UNIQUE_PRE_ADJUDICATION_UTILITY_NOT_FOUND"
            if verdict in {"PRE_ADJUDICATION_CAUSAL_PARITY", "PRE_ADJUDICATION_NO_UNIQUE_ADVANTAGE"}
            else "REQUIRES_REVIEW"
        ),
        "evaluation_families": 10,
        "identities_per_family": identities,
        "metrics": metrics,
        "rows": rows,
        "transport_failures": transport_failures,
        "verdict": verdict,
    }
