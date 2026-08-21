"""Frozen RCDL-002 contract bindings used without semantic modification."""

from __future__ import annotations

from pathlib import Path

from rcdl.model import Clause

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]

TEST_EVIDENCE_HOOK = "test_evidence_guard"
REVIEW_PATCH_HOOK = "review_patch_guard"
APPROVAL_TEST_HOOK = "approval_test_guard"
RECOVERY_OBSERVATION_HOOK = "recovery_observation_guard"
PLANNER_NOTE_HOOK = "planner_review_note_guard"

ALL_HOOKS = frozenset(
    {
        TEST_EVIDENCE_HOOK,
        REVIEW_PATCH_HOOK,
        APPROVAL_TEST_HOOK,
        RECOVERY_OBSERVATION_HOOK,
        PLANNER_NOTE_HOOK,
    }
)
TARGET_CLAUSE_IDS = frozenset(
    {
        "workflow.test_result_matches_patch",
        "workflow.review_inspects_current_patch",
        "workflow.approval_requires_passing_tests",
        "workflow.recovery_requires_fresh_observation",
    }
)
SPURIOUS_CONTROL_IDS = frozenset({"workflow.planner_review_note_required"})


def frozen_clauses() -> tuple[Clause, ...]:
    return tuple(
        Clause.from_path(path)
        for path in sorted((EXPERIMENT_ROOT / "clauses").glob("*.json"))
    )


def clauses_by_id() -> dict[str, Clause]:
    return {clause.id: clause for clause in frozen_clauses()}


def hooks_by_clause_id() -> dict[str, str]:
    return {clause.id: clause.hook for clause in frozen_clauses()}
