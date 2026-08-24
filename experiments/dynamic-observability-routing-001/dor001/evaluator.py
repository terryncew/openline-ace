from __future__ import annotations

from dataclasses import asdict
from statistics import mean, median
from typing import Any

from .core import (
    EvidenceState,
    EqualBudgetWidePolicy,
    FixedHeadlinePolicy,
    Observation,
    Router,
)
from .fixture import Scenario, frozen_manifest, frozen_scenarios


class ExternalOracle:
    """Frozen evaluator oracle. It is never passed to any measurement policy."""

    @staticmethod
    def transition_resolved(scenario: Scenario, observations: tuple[Observation, ...]) -> bool:
        if scenario.true_state != "transition":
            return False
        allowed = set(scenario.oracle_diagnostic_channels)
        for obs in observations:
            if obs.channel_id not in allowed or obs.value < 1.0:
                continue
            reveal_t = scenario.reveal_times.get(obs.channel_id)
            if reveal_t is not None and obs.t >= reveal_t:
                return True
        return False

    @staticmethod
    def stable_resolved(scenario: Scenario, observations: tuple[Observation, ...], t: int) -> bool:
        # A stable state is not treated as resolved early merely because diagnostics
        # remain quiet. This prevents cheap "nothing happened" declarations.
        if scenario.true_state != "stable" or t < scenario.horizon:
            return False
        required = {"sentinel", "headline"}
        observed = {o.channel_id for o in observations if o.t <= t and o.value < 1.0}
        return required.issubset(observed)

    def resolved(self, scenario: Scenario, observations: tuple[Observation, ...], t: int) -> bool:
        return self.transition_resolved(scenario, observations) or self.stable_resolved(scenario, observations, t)


def replay_policy(scenario: Scenario, policy_name: str) -> dict[str, Any]:
    manifest = frozen_manifest()
    if policy_name == "dor":
        policy = Router(manifest)
    elif policy_name == "fixed_headline":
        policy = FixedHeadlinePolicy(manifest)
    elif policy_name == "equal_budget_wide":
        policy = EqualBudgetWidePolicy(manifest)
    else:
        raise ValueError(policy_name)

    oracle = ExternalOracle()
    observations: list[Observation] = []
    receipts: list[dict[str, Any]] = []
    total_cost = 0
    false_resolution_events = 0
    t_resolved: int | None = None

    for t in range(scenario.horizon + 1):
        available_receipts = tuple(r for r in scenario.prior_receipts if r.issued_at <= t)
        evidence = EvidenceState(
            as_of=t,
            receipts=available_receipts,
            observations=tuple(observations),
        )
        measurement_receipt = policy.select(scenario.scenario_id, evidence)
        total_cost += measurement_receipt.budget_spent
        new_observations = tuple(
            Observation(t=t, channel_id=channel_id, value=scenario.value_at(channel_id, t))
            for channel_id in measurement_receipt.selected_channels
        )
        observations.extend(new_observations)
        oracle_now = oracle.resolved(scenario, tuple(observations), t)
        # Measurement policies are routing-only. They cannot declare the state
        # resolved; only the frozen external oracle can end the replay.
        policy_declared = False
        receipts.append({
            **asdict(measurement_receipt),
            "observations": [asdict(o) for o in new_observations],
            "oracle_resolved_after_measurement": oracle_now,
            "policy_declared_transition": policy_declared,
        })
        if oracle_now:
            t_resolved = t
            break

    return {
        "scenario_id": scenario.scenario_id,
        "partition": scenario.partition,
        "mechanism_id": scenario.mechanism_id,
        "true_state": scenario.true_state,
        "policy": policy_name,
        "t_resolved": t_resolved,
        "false_resolution_events": false_resolution_events,
        "telemetry_cost": total_cost,
        "measurement_receipts": receipts,
    }


def summarize(rows: list[dict[str, Any]], policy: str) -> dict[str, Any]:
    subset = [r for r in rows if r["policy"] == policy and r["partition"] == "heldout"]
    transition_rows = [r for r in subset if r["true_state"] == "transition"]
    resolved_times = [r["t_resolved"] for r in transition_rows if r["t_resolved"] is not None]
    return {
        "heldout_cases": len(subset),
        "heldout_transition_cases": len(transition_rows),
        "resolved_transition_cases": len(resolved_times),
        "mean_t_resolved": mean(resolved_times) if resolved_times else None,
        "median_t_resolved": median(resolved_times) if resolved_times else None,
        "false_resolution_events": sum(r["false_resolution_events"] for r in subset),
        "mean_telemetry_cost": mean(r["telemetry_cost"] for r in subset) if subset else None,
    }


def run_all() -> dict[str, Any]:
    scenarios = frozen_scenarios()
    rows = [
        replay_policy(scenario, policy)
        for scenario in scenarios
        for policy in ("dor", "fixed_headline", "equal_budget_wide")
    ]

    heldout = [s for s in scenarios if s.partition == "heldout" and s.true_state == "transition"]
    deltas: list[dict[str, Any]] = []
    for scenario in heldout:
        by_policy = {
            r["policy"]: r for r in rows
            if r["scenario_id"] == scenario.scenario_id
        }
        t_dor = by_policy["dor"]["t_resolved"]
        t_default = by_policy["fixed_headline"]["t_resolved"]
        t_wide = by_policy["equal_budget_wide"]["t_resolved"]
        deltas.append({
            "scenario_id": scenario.scenario_id,
            "delta_tau_vs_fixed_headline": None if t_dor is None or t_default is None else t_default - t_dor,
            "delta_tau_vs_equal_budget_wide": None if t_dor is None or t_wide is None else t_wide - t_dor,
            "t_dor": t_dor,
            "t_fixed_headline": t_default,
            "t_equal_budget_wide": t_wide,
        })

    comparable_fixed = [d["delta_tau_vs_fixed_headline"] for d in deltas if d["delta_tau_vs_fixed_headline"] is not None]
    comparable_wide = [d["delta_tau_vs_equal_budget_wide"] for d in deltas if d["delta_tau_vs_equal_budget_wide"] is not None]
    summaries = {p: summarize(rows, p) for p in ("dor", "fixed_headline", "equal_budget_wide")}

    equal_budget = all(
        all(rec["budget_limit"] == 2 and rec["budget_spent"] == 2 for rec in r["measurement_receipts"])
        for r in rows
    )
    sentinel_coverage = all(
        all("sentinel" in rec["selected_channels"] for rec in r["measurement_receipts"])
        for r in rows
    )

    # Frozen promotion rule. This is a synthetic mechanism audit, not an external
    # validity claim. DOR must beat both baselines in median held-out resolution
    # time, spend the same per-tick budget, preserve sentinel coverage, and not
    # create more false-resolution events than either comparator.
    dor_false = summaries["dor"]["false_resolution_events"]
    fixed_false = summaries["fixed_headline"]["false_resolution_events"]
    wide_false = summaries["equal_budget_wide"]["false_resolution_events"]
    wins_fixed = median(comparable_fixed) > 0 if comparable_fixed else False
    wins_wide = median(comparable_wide) > 0 if comparable_wide else False
    safety_ok = dor_false <= min(fixed_false, wide_false)

    if equal_budget and sentinel_coverage and wins_fixed and wins_wide and safety_ok:
        verdict = "SYNTHETIC_ROUTING_ADVANTAGE"
    elif not equal_budget or not sentinel_coverage or dor_false > min(fixed_false, wide_false):
        verdict = "ROUTING_ADVANTAGE_REJECTED"
    else:
        verdict = "NO_ROUTING_ADVANTAGE"

    return {
        "schema": "openline.ace.dor001.result.v1",
        "experiment_id": "DOR-001",
        "claim_boundary": "synthetic observability-routing mechanism audit only; no predictive, safety, or runtime-authority claim",
        "runtime_permission": "NONE",
        "policy_authority": "NONE",
        "primary_metrics": {
            "median_delta_tau_vs_fixed_headline": median(comparable_fixed) if comparable_fixed else None,
            "median_delta_tau_vs_equal_budget_wide": median(comparable_wide) if comparable_wide else None,
            "equal_budget_per_tick": equal_budget,
            "mandatory_sentinel_coverage": sentinel_coverage,
            "false_resolution_events": {
                "dor": dor_false,
                "fixed_headline": fixed_false,
                "equal_budget_wide": wide_false,
            },
        },
        "policy_summaries": summaries,
        "heldout_deltas": deltas,
        "verdict": verdict,
        "rows": rows,
    }
