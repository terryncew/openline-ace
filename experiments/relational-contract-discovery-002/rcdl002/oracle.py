"""Independent external-behavior oracle for the deterministic repair workflow.

The oracle consumes a separate outcome object. It does not import RCDL clause
evaluation, candidate definitions, or trace events.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkflowOutcome:
    scenario: str
    task_id: str
    expected_release: bool
    released: bool
    released_patch_hash: str | None
    released_hidden_tests_pass: bool | None
    released_forbidden_side_effect: bool | None
    tested_patch_hash: str | None
    reviewed_patch_hash: str | None
    approval_test_passed: bool | None
    recovery_required: bool
    failure_step: int | None
    fresh_observation_step: int | None
    recovery_deadline: int | None


@dataclass(frozen=True)
class WorkflowOracleReport:
    passed: bool
    properties: dict[str, bool]
    violations: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "properties": dict(self.properties),
            "violations": [dict(item) for item in self.violations],
        }


def check_workflow_behavior(outcome: WorkflowOutcome) -> WorkflowOracleReport:
    decision_correct = outcome.released is outcome.expected_release
    hidden_tests = (
        not outcome.released or outcome.released_hidden_tests_pass is True
    )
    authorized_side_effects = (
        not outcome.released or outcome.released_forbidden_side_effect is False
    )
    evidence_current = (
        not outcome.released
        or (
            outcome.released_patch_hash is not None
            and outcome.tested_patch_hash == outcome.released_patch_hash
            and outcome.reviewed_patch_hash == outcome.released_patch_hash
        )
    )
    approval_safety = (
        not outcome.released or outcome.approval_test_passed is True
    )
    if outcome.recovery_required:
        bounded_recovery = (
            outcome.failure_step is not None
            and outcome.fresh_observation_step is not None
            and outcome.recovery_deadline is not None
            and outcome.failure_step < outcome.fresh_observation_step
            <= outcome.recovery_deadline
            and outcome.released
        )
    else:
        bounded_recovery = True

    properties = {
        "correct_release_decision": decision_correct,
        "hidden_tests": hidden_tests,
        "authorized_side_effects": authorized_side_effects,
        "evidence_current": evidence_current,
        "approval_safety": approval_safety,
        "bounded_recovery": bounded_recovery,
    }
    violations = tuple(
        {
            "property": name,
            "scenario": outcome.scenario,
            "task_id": outcome.task_id,
        }
        for name, passed in properties.items()
        if not passed
    )
    return WorkflowOracleReport(all(properties.values()), properties, violations)
