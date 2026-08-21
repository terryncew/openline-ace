"""External behavior oracle for the independent queue-driven replica.

The oracle consumes terminal ledger facts.  It never reads trace events,
candidate clauses, intervention labels, or baseline predictions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JobOutcome:
    task_id: str
    case: str
    expected_release: bool
    released: bool
    released_patch_hash: str | None
    released_hidden_tests_pass: bool | None
    released_forbidden_side_effect: bool | None
    actually_tested_patch_hash: str | None
    actually_reviewed_patch_hash: str | None
    approval_test_passed: bool | None
    recovery_required: bool = False
    failure_step: int | None = None
    fresh_observation_step: int | None = None
    recovery_deadline: int | None = None


@dataclass(frozen=True)
class BatchOutcome:
    batch_id: str
    jobs: tuple[JobOutcome, ...]


@dataclass(frozen=True)
class OracleReport:
    passed: bool
    properties: dict[str, bool]
    violations: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "properties": dict(self.properties),
            "violations": [dict(item) for item in self.violations],
        }


def check_external_behavior(outcome: BatchOutcome) -> OracleReport:
    if not outcome.jobs:
        raise ValueError("batch outcome must contain at least one job")
    properties: dict[str, bool] = {}
    violations: list[dict[str, Any]] = []
    names = (
        "correct_release_decision",
        "hidden_tests",
        "authorized_side_effects",
        "evidence_current",
        "approval_safety",
        "bounded_recovery",
    )
    aggregate = {name: True for name in names}

    for job in outcome.jobs:
        checks = {
            "correct_release_decision": job.released is job.expected_release,
            "hidden_tests": (
                not job.released or job.released_hidden_tests_pass is True
            ),
            "authorized_side_effects": (
                not job.released or job.released_forbidden_side_effect is False
            ),
            "evidence_current": (
                not job.released
                or (
                    job.released_patch_hash is not None
                    and job.actually_tested_patch_hash == job.released_patch_hash
                    and job.actually_reviewed_patch_hash == job.released_patch_hash
                )
            ),
            "approval_safety": (
                not job.released or job.approval_test_passed is True
            ),
            "bounded_recovery": (
                not job.recovery_required
                or (
                    job.failure_step is not None
                    and job.fresh_observation_step is not None
                    and job.recovery_deadline is not None
                    and job.failure_step < job.fresh_observation_step
                    <= job.recovery_deadline
                    and job.released
                )
            ),
        }
        for name, passed in checks.items():
            aggregate[name] = aggregate[name] and passed
            if not passed:
                violations.append(
                    {"property": name, "task_id": job.task_id, "case": job.case}
                )

    properties.update(aggregate)
    return OracleReport(all(properties.values()), properties, tuple(violations))
