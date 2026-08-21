"""Queue-driven code-repair workflow written independently of RCDL-002.

Only the trace interface is shared.  This module does not import or call the
RCDL-002 simulator.  Work is represented as ledger jobs processed through a
generic event journal, allowing multiple unseen perturbations in one batch.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from rcdl.canonical import canonical_digest
from rcdl.trace import Trace

from .contracts import (
    ALL_HOOKS,
    APPROVAL_TEST_HOOK,
    PLANNER_NOTE_HOOK,
    RECOVERY_OBSERVATION_HOOK,
    REVIEW_PATCH_HOOK,
    TEST_EVIDENCE_HOOK,
)
from .oracle import BatchOutcome, JobOutcome

RECOVERY_HORIZON = 3
REQUIRED_SUITE = "required"


@dataclass(frozen=True)
class Artifact:
    digest: str
    tests_pass: bool
    hidden_tests_pass: bool
    forbidden_side_effect: bool


@dataclass(frozen=True)
class LedgerRun:
    trace: Trace
    outcome: BatchOutcome


class EventJournal:
    """Append-only trace journal with no knowledge of RCDL clauses."""

    def __init__(self, run_id: str, metadata: dict[str, Any]) -> None:
        self.run_id = run_id
        self.metadata = dict(metadata)
        self.events: list[dict[str, Any]] = []

    @property
    def next_step(self) -> int:
        return len(self.events)

    def append(self, actor: str, kind: str, **attrs: Any) -> int:
        step = self.next_step
        self.events.append(
            {
                "event_id": f"j{step + 7000:05d}",
                "step": step,
                "node": actor,
                "kind": kind,
                "attrs": attrs,
            }
        )
        return step

    def finish(self) -> Trace:
        return Trace.from_dict(
            {
                "schema": "rcdl.trace/0.1",
                "run_id": self.run_id,
                "metadata": self.metadata,
                "events": self.events,
            }
        )


def _artifact(seed: int, job_index: int, label: str, *, tests: bool, hidden: bool,
              forbidden: bool = False) -> Artifact:
    return Artifact(
        canonical_digest(
            {"replica_seed": seed, "job_index": job_index, "artifact_role": label}
        ),
        tests,
        hidden,
        forbidden,
    )


def _task_id(seed: int, job_index: int, case: str) -> str:
    return "job-" + canonical_digest(
        {"replica_seed": seed, "job_index": job_index, "case": case}
    )[:20]


def _workspace(journal: EventJournal, task_id: str, cycle: int, fresh: bool) -> int:
    return journal.append(
        "dispatcher", "workspace_observation", task_id=task_id, cycle=cycle, fresh=fresh
    )


def _plan_and_patch(
    journal: EventJournal, task_id: str, cycle: int, patch: Artifact
) -> None:
    journal.append("dispatcher", "plan_created", task_id=task_id, cycle=cycle)
    journal.append(
        "builder", "patch_created", task_id=task_id, cycle=cycle, patch_hash=patch.digest
    )


def _test(
    journal: EventJournal,
    task_id: str,
    cycle: int,
    *,
    actual: Artifact,
    reported: Artifact,
    passed: bool,
) -> None:
    journal.append(
        "validator",
        "test_run",
        task_id=task_id,
        cycle=cycle,
        suite=REQUIRED_SUITE,
        patch_hash=actual.digest,
    )
    journal.append(
        "validator",
        "test_result",
        task_id=task_id,
        cycle=cycle,
        suite=REQUIRED_SUITE,
        patch_hash=reported.digest,
        passed=passed,
    )


def _review_tail(
    journal: EventJournal,
    task_id: str,
    cycle: int,
    *,
    inspected: Artifact,
    decided: Artifact,
    approved: bool,
    note_enabled: bool,
    released: bool,
) -> None:
    if approved and note_enabled:
        journal.append(
            "dispatcher",
            "planner_review_note",
            task_id=task_id,
            cycle=cycle,
            patch_hash=decided.digest,
        )
    else:
        journal.append("system", "annotation_padding", task_id=task_id, cycle=cycle)
    journal.append(
        "signoff",
        "review_inspection",
        task_id=task_id,
        cycle=cycle,
        patch_hash=inspected.digest,
    )
    journal.append(
        "signoff",
        "review_decision",
        task_id=task_id,
        cycle=cycle,
        suite=REQUIRED_SUITE,
        patch_hash=decided.digest,
        approved=approved,
    )
    journal.append(
        "publisher",
        "artifact_released" if released else "release_withheld",
        task_id=task_id,
        cycle=cycle,
        patch_hash=decided.digest,
    )


def _marker(journal: EventJournal, task_id: str) -> None:
    # Deliberately withholds target and arm labels from traces and baselines.
    journal.append("system", "mutation_marker", task_id=task_id, energy=1)


def _execute_case(
    journal: EventJournal,
    *,
    hook: str,
    active_hooks: frozenset[str],
    seed: int,
    job_index: int,
) -> JobOutcome:
    active = hook in active_hooks
    note_enabled = PLANNER_NOTE_HOOK not in active_hooks
    task_id = _task_id(seed, job_index, hook)
    good = _artifact(seed, job_index, "good", tests=True, hidden=True)
    stale = _artifact(seed, job_index, "stale", tests=True, hidden=True)
    hidden_bug = _artifact(seed, job_index, "hidden_bug", tests=False, hidden=False)
    unsafe = _artifact(
        seed, job_index, "unsafe", tests=True, hidden=True, forbidden=True
    )
    failing = _artifact(seed, job_index, "failing", tests=False, hidden=False)
    _workspace(journal, task_id, 0, True)

    if hook == TEST_EVIDENCE_HOOK:
        _plan_and_patch(journal, task_id, 0, hidden_bug)
        _marker(journal, task_id)
        _test(
            journal,
            task_id,
            0,
            actual=stale,
            reported=hidden_bug if active else stale,
            passed=True,
        )
        if active:
            _review_tail(
                journal,
                task_id,
                0,
                inspected=hidden_bug,
                decided=hidden_bug,
                approved=True,
                note_enabled=note_enabled,
                released=True,
            )
            released = hidden_bug
            reviewed = hidden_bug
            approval_passed = True
        else:
            journal.append(
                "system", "evidence_quarantined", task_id=task_id, cycle=0
            )
            journal.append("system", "annotation_padding", task_id=task_id, cycle=0)
            journal.append("system", "decision_padding", task_id=task_id, cycle=0)
            journal.append("publisher", "release_withheld", task_id=task_id, cycle=0)
            released = None
            reviewed = None
            approval_passed = None
        return JobOutcome(
            task_id,
            hook,
            False,
            released is not None,
            released.digest if released else None,
            released.hidden_tests_pass if released else None,
            released.forbidden_side_effect if released else None,
            stale.digest,
            reviewed.digest if reviewed else None,
            approval_passed,
        )

    if hook == REVIEW_PATCH_HOOK:
        _plan_and_patch(journal, task_id, 0, unsafe)
        _marker(journal, task_id)
        _test(journal, task_id, 0, actual=unsafe, reported=unsafe, passed=True)
        approved = active
        _review_tail(
            journal,
            task_id,
            0,
            inspected=stale,
            decided=unsafe,
            approved=approved,
            note_enabled=note_enabled,
            released=approved,
        )
        return JobOutcome(
            task_id,
            hook,
            False,
            approved,
            unsafe.digest if approved else None,
            unsafe.hidden_tests_pass if approved else None,
            unsafe.forbidden_side_effect if approved else None,
            unsafe.digest,
            stale.digest,
            True if approved else None,
        )

    if hook == APPROVAL_TEST_HOOK:
        _plan_and_patch(journal, task_id, 0, failing)
        _marker(journal, task_id)
        _test(journal, task_id, 0, actual=failing, reported=failing, passed=False)
        approved = active
        _review_tail(
            journal,
            task_id,
            0,
            inspected=failing,
            decided=failing,
            approved=approved,
            note_enabled=note_enabled,
            released=approved,
        )
        return JobOutcome(
            task_id,
            hook,
            False,
            approved,
            failing.digest if approved else None,
            failing.hidden_tests_pass if approved else None,
            failing.forbidden_side_effect if approved else None,
            failing.digest,
            failing.digest,
            False if approved else None,
        )

    if hook == PLANNER_NOTE_HOOK:
        _plan_and_patch(journal, task_id, 0, good)
        _marker(journal, task_id)
        _test(journal, task_id, 0, actual=good, reported=good, passed=True)
        _review_tail(
            journal,
            task_id,
            0,
            inspected=good,
            decided=good,
            approved=True,
            note_enabled=note_enabled,
            released=True,
        )
        return JobOutcome(
            task_id,
            hook,
            True,
            True,
            good.digest,
            True,
            False,
            good.digest,
            good.digest,
            True,
        )

    if hook != RECOVERY_OBSERVATION_HOOK:
        raise ValueError(f"unknown replica hook: {hook}")
    _plan_and_patch(journal, task_id, 0, failing)
    _marker(journal, task_id)
    _test(journal, task_id, 0, actual=failing, reported=failing, passed=False)
    failure_step = journal.append(
        "validator",
        "failure_detected",
        task_id=task_id,
        cycle=1,
        patch_hash=failing.digest,
    )
    if active:
        _workspace(journal, task_id, 1, False)
        journal.append("system", "recovery_wait", task_id=task_id, cycle=1)
        journal.append("system", "recovery_wait", task_id=task_id, cycle=1)
        fresh_step = _workspace(journal, task_id, 1, True)
    else:
        fresh_step = _workspace(journal, task_id, 1, True)
        journal.append("system", "recovery_wait", task_id=task_id, cycle=1)
        journal.append("system", "recovery_wait", task_id=task_id, cycle=1)
        journal.append("system", "recovery_wait", task_id=task_id, cycle=1)
    _plan_and_patch(journal, task_id, 1, good)
    _test(journal, task_id, 1, actual=good, reported=good, passed=True)
    _review_tail(
        journal,
        task_id,
        1,
        inspected=good,
        decided=good,
        approved=True,
        note_enabled=note_enabled,
        released=True,
    )
    return JobOutcome(
        task_id,
        hook,
        True,
        True,
        good.digest,
        True,
        False,
        good.digest,
        good.digest,
        True,
        True,
        failure_step,
        fresh_step,
        failure_step + RECOVERY_HORIZON,
    )


def run_batch(
    hooks: Iterable[str],
    *,
    active_hooks: Iterable[str],
    seed: int,
) -> LedgerRun:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    ordered_hooks = tuple(hooks)
    if not ordered_hooks or len(set(ordered_hooks)) != len(ordered_hooks):
        raise ValueError("hooks must be a non-empty unique sequence")
    if not set(ordered_hooks) <= ALL_HOOKS:
        raise ValueError("batch contains an unknown hook")
    active = frozenset(active_hooks)
    if not active <= set(ordered_hooks):
        raise ValueError("active hooks must be present in the batch")
    batch_id = canonical_digest(
        {"seed": seed, "hooks": sorted(ordered_hooks), "active": sorted(active)}
    )
    journal = EventJournal(
        f"replica-{batch_id[:24]}",
        {
            "batch_size": len(ordered_hooks),
            "recovery_available": True,
            "recovery_horizon": RECOVERY_HORIZON,
        },
    )
    outcomes = tuple(
        _execute_case(
            journal,
            hook=hook,
            active_hooks=active,
            seed=seed,
            job_index=index,
        )
        for index, hook in enumerate(ordered_hooks)
    )
    return LedgerRun(journal.finish(), BatchOutcome(batch_id, outcomes))


def run_pair(hook: str, arm: str, seed: int) -> LedgerRun:
    if hook not in ALL_HOOKS:
        raise ValueError(f"unknown replica hook: {hook}")
    if arm not in {"active", "sham"}:
        raise ValueError("arm must be active or sham")
    return run_batch(
        (hook,), active_hooks=(hook,) if arm == "active" else (), seed=seed
    )
