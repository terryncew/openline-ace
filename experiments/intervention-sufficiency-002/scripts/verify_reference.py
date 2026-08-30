from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    result = json.loads(
        (ROOT / "results" / "reference_result.json").read_text(encoding="utf-8")
    )
    errors: list[str] = []
    if result.get("status") != "MECHANICS_PASS_UNITREE_EXTERNAL_FROZEN":
        errors.append("status")
    if result.get("external_candidate_status") != "COMPLETE_RETROSPECTIVE_REPLAY":
        errors.append("external_candidate_status")
    if (
        result.get("external_verdict")
        != "INSUFFICIENT_STATE_SPECIFIC_INTERVENTION_CONTRAST"
    ):
        errors.append("external_verdict")
    reports = result.get("reports", {})
    expected = {
        "deterministic_global_control": (
            "INSUFFICIENT_STATE_SPECIFIC_INTERVENTION_CONTRAST"
        ),
        "deterministic_state_specific_control": (
            "SUFFICIENT_FOR_FRESH_TRANSITION_CONFIRMATION"
        ),
        "stochastic_state_specific_control": (
            "SUFFICIENT_FOR_FRESH_TRANSITION_CONFIRMATION"
        ),
        "validated_model_state_specific_control": (
            "SUFFICIENT_FOR_FRESH_TRANSITION_CONFIRMATION"
        ),
    }
    for name, verdict in expected.items():
        report = reports.get(name, {})
        if report.get("verdict") != verdict:
            errors.append(f"verdict:{name}")
        if report.get("capacity_selector_training_authorized") is not False:
            errors.append(f"selector:{name}")
    global_report = reports.get("deterministic_global_control", {})
    global_gates = global_report.get("gates", {})
    for name in (
        "state_dependent_action_lag_strata",
        "bidirectional_remedy_divergent_risk_pairs",
        "global_action_delay_cell_accuracy",
    ):
        if global_gates.get(name, {}).get("passed") is not False:
            errors.append(f"global_control:{name}")

    print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
