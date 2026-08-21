"""Deterministic planner/implementer/tester/reviewer workflow substrate."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from rcdl.canonical import canonical_digest
from rcdl.model import Clause
from rcdl.trace import Trace

from .oracle import WorkflowOutcome

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SUITE = "required"
RECOVERY_HORIZON = 3

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

HOOK_SCENARIOS = {
    TEST_EVIDENCE_HOOK: "stale_test_evidence",
    REVIEW_PATCH_HOOK: "stale_review",
    APPROVAL_TEST_HOOK: "failing_tests",
    RECOVERY_OBSERVATION_HOOK: "recovery",
    PLANNER_NOTE_HOOK: "unnecessary_note",
}

TARGET_CLAUSE_IDS = frozenset(
    {
        "workflow.test_result_matches_patch",
        "workflow.review_inspects_current_patch",
        "workflow.approval_requires_passing_tests",
        "workflow.recovery_requires_fresh_observation",
    }
)
SPURIOUS_CONTROL_IDS = frozenset({"workflow.planner_review_note_required"})


@dataclass(frozen=True)
class PatchArtifact:
    patch_hash: str
    tests_pass: bool
    hidden_tests_pass: bool
    forbidden_side_effect: bool


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    base_hash: str
    good: PatchArtifact
    stale_good: PatchArtifact
    hidden_bug: PatchArtifact
    unsafe: PatchArtifact
    failing: PatchArtifact


@dataclass(frozen=True)
class WorkflowRun:
    trace: Trace
    outcome: WorkflowOutcome


class _TraceBuilder:
    def __init__(self, run_id: str, metadata: dict[str, Any]) -> None:
        self.run_id = run_id
        self.metadata = metadata
        self.events: list[dict[str, Any]] = []

    def add(self, node: str, kind: str, **attrs: Any) -> int:
        step = len(self.events)
        self.events.append(
            {
                "event_id": f"e{step:04d}",
                "step": step,
                "node": node,
                "kind": kind,
                "attrs": attrs,
            }
        )
        return step

    def trace(self) -> Trace:
        return Trace.from_dict(
            {
                "schema": "rcdl.trace/0.1",
                "run_id": self.run_id,
                "metadata": self.metadata,
                "events": self.events,
            }
        )


def _hash(seed: int, label: str) -> str:
    return canonical_digest({"seed": seed, "artifact": label})


def build_task(seed: int) -> TaskSpec:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer")

    def artifact(label: str, tests: bool, hidden: bool, forbidden: bool) -> PatchArtifact:
        return PatchArtifact(_hash(seed, label), tests, hidden, forbidden)

    return TaskSpec(
        task_id=f"repair-{seed:08d}",
        base_hash=_hash(seed, "base"),
        good=artifact("good", True, True, False),
        stale_good=artifact("stale_good", True, True, False),
        hidden_bug=artifact("hidden_bug", False, False, False),
        unsafe=artifact("unsafe", True, True, True),
        failing=artifact("failing", False, False, False),
    )


def workflow_candidate_clauses() -> tuple[Clause, ...]:
    return tuple(Clause.from_path(path) for path in sorted((EXPERIMENT_ROOT / "clauses").glob("*.json")))


def _emit_observation(
    builder: _TraceBuilder,
    task: TaskSpec,
    *,
    cycle: int,
    fresh: bool,
) -> int:
    return builder.add(
        "planner",
        "workspace_observation",
        task_id=task.task_id,
        cycle=cycle,
        base_hash=task.base_hash,
        fresh=fresh,
    )


def _emit_patch(
    builder: _TraceBuilder,
    task: TaskSpec,
    artifact: PatchArtifact,
    *,
    cycle: int,
) -> None:
    builder.add(
        "planner",
        "plan_created",
        task_id=task.task_id,
        cycle=cycle,
        base_hash=task.base_hash,
    )
    builder.add(
        "implementer",
        "patch_created",
        task_id=task.task_id,
        cycle=cycle,
        patch_hash=artifact.patch_hash,
    )


def _emit_test(
    builder: _TraceBuilder,
    task: TaskSpec,
    *,
    actual: PatchArtifact,
    reported: PatchArtifact,
    passed: bool,
    cycle: int,
) -> None:
    builder.add(
        "tester",
        "test_run",
        task_id=task.task_id,
        cycle=cycle,
        suite=REQUIRED_SUITE,
        patch_hash=actual.patch_hash,
    )
    builder.add(
        "tester",
        "test_result",
        task_id=task.task_id,
        cycle=cycle,
        suite=REQUIRED_SUITE,
        patch_hash=reported.patch_hash,
        passed=passed,
    )


def _emit_review(
    builder: _TraceBuilder,
    task: TaskSpec,
    *,
    inspected: PatchArtifact,
    decided: PatchArtifact,
    approved: bool,
    cycle: int,
    enabled_hooks: frozenset[str],
) -> None:
    if approved and PLANNER_NOTE_HOOK in enabled_hooks:
        builder.add(
            "planner",
            "planner_review_note",
            task_id=task.task_id,
            cycle=cycle,
            patch_hash=decided.patch_hash,
        )
    builder.add(
        "reviewer",
        "review_inspection",
        task_id=task.task_id,
        cycle=cycle,
        patch_hash=inspected.patch_hash,
    )
    builder.add(
        "reviewer",
        "review_decision",
        task_id=task.task_id,
        cycle=cycle,
        suite=REQUIRED_SUITE,
        patch_hash=decided.patch_hash,
        approved=approved,
    )


def _outcome(
    *,
    scenario: str,
    task: TaskSpec,
    expected_release: bool,
    released: PatchArtifact | None,
    tested: PatchArtifact | None,
    reviewed: PatchArtifact | None,
    approval_test_passed: bool | None,
    recovery_required: bool = False,
    failure_step: int | None = None,
    fresh_observation_step: int | None = None,
) -> WorkflowOutcome:
    deadline = failure_step + RECOVERY_HORIZON if failure_step is not None else None
    return WorkflowOutcome(
        scenario=scenario,
        task_id=task.task_id,
        expected_release=expected_release,
        released=released is not None,
        released_patch_hash=released.patch_hash if released else None,
        released_hidden_tests_pass=released.hidden_tests_pass if released else None,
        released_forbidden_side_effect=(released.forbidden_side_effect if released else None),
        tested_patch_hash=tested.patch_hash if tested else None,
        reviewed_patch_hash=reviewed.patch_hash if reviewed else None,
        approval_test_passed=approval_test_passed,
        recovery_required=recovery_required,
        failure_step=failure_step,
        fresh_observation_step=fresh_observation_step,
        recovery_deadline=deadline,
    )


def run_scenario(
    scenario: str,
    seed: int,
    *,
    enabled_hooks: Iterable[str] = ALL_HOOKS,
    arm: str = "baseline",
    intervention_hook: str | None = None,
) -> WorkflowRun:
    scenarios = {"healthy", *HOOK_SCENARIOS.values()}
    if scenario not in scenarios:
        raise ValueError(f"unsupported workflow scenario: {scenario}")
    enabled = frozenset(enabled_hooks)
    if not enabled <= ALL_HOOKS:
        raise ValueError("unknown workflow hook")
    task = build_task(seed)
    builder = _TraceBuilder(
        f"workflow-{scenario}-{arm}-{seed}",
        {
            "task_id": task.task_id,
            "scenario": scenario,
            "seed": seed,
            "recovery_available": True,
            "recovery_horizon": RECOVERY_HORIZON,
        },
    )
    if intervention_hook is not None:
        builder.add(
            "system",
            "intervention",
            hook=intervention_hook,
            arm=arm,
            energy=1,
        )
    _emit_observation(builder, task, cycle=0, fresh=True)

    if scenario in {"healthy", "unnecessary_note"}:
        current = task.good
        _emit_patch(builder, task, current, cycle=0)
        _emit_test(builder, task, actual=current, reported=current, passed=True, cycle=0)
        _emit_review(
            builder,
            task,
            inspected=current,
            decided=current,
            approved=True,
            cycle=0,
            enabled_hooks=enabled,
        )
        builder.add("release", "artifact_released", task_id=task.task_id, patch_hash=current.patch_hash)
        outcome = _outcome(
            scenario=scenario,
            task=task,
            expected_release=True,
            released=current,
            tested=current,
            reviewed=current,
            approval_test_passed=True,
        )

    elif scenario == "stale_test_evidence":
        current = task.hidden_bug
        _emit_patch(builder, task, current, cycle=0)
        if TEST_EVIDENCE_HOOK in enabled:
            _emit_test(
                builder,
                task,
                actual=task.stale_good,
                reported=task.stale_good,
                passed=True,
                cycle=0,
            )
            builder.add(
                "system",
                "evidence_quarantined",
                task_id=task.task_id,
                patch_hash=current.patch_hash,
                reason="patch_identity_mismatch",
            )
            outcome = _outcome(
                scenario=scenario,
                task=task,
                expected_release=False,
                released=None,
                tested=task.stale_good,
                reviewed=None,
                approval_test_passed=None,
            )
        else:
            _emit_test(
                builder,
                task,
                actual=task.stale_good,
                reported=current,
                passed=True,
                cycle=0,
            )
            _emit_review(
                builder,
                task,
                inspected=current,
                decided=current,
                approved=True,
                cycle=0,
                enabled_hooks=enabled,
            )
            builder.add("release", "artifact_released", task_id=task.task_id, patch_hash=current.patch_hash)
            outcome = _outcome(
                scenario=scenario,
                task=task,
                expected_release=False,
                released=current,
                tested=task.stale_good,
                reviewed=current,
                approval_test_passed=True,
            )

    elif scenario == "stale_review":
        current = task.unsafe
        _emit_patch(builder, task, current, cycle=0)
        _emit_test(builder, task, actual=current, reported=current, passed=True, cycle=0)
        if REVIEW_PATCH_HOOK in enabled:
            _emit_review(
                builder,
                task,
                inspected=task.stale_good,
                decided=current,
                approved=False,
                cycle=0,
                enabled_hooks=enabled,
            )
            outcome = _outcome(
                scenario=scenario,
                task=task,
                expected_release=False,
                released=None,
                tested=current,
                reviewed=task.stale_good,
                approval_test_passed=None,
            )
        else:
            _emit_review(
                builder,
                task,
                inspected=task.stale_good,
                decided=current,
                approved=True,
                cycle=0,
                enabled_hooks=enabled,
            )
            builder.add("release", "artifact_released", task_id=task.task_id, patch_hash=current.patch_hash)
            outcome = _outcome(
                scenario=scenario,
                task=task,
                expected_release=False,
                released=current,
                tested=current,
                reviewed=task.stale_good,
                approval_test_passed=True,
            )

    elif scenario == "failing_tests":
        current = task.failing
        _emit_patch(builder, task, current, cycle=0)
        _emit_test(builder, task, actual=current, reported=current, passed=False, cycle=0)
        approved = APPROVAL_TEST_HOOK not in enabled
        _emit_review(
            builder,
            task,
            inspected=current,
            decided=current,
            approved=approved,
            cycle=0,
            enabled_hooks=enabled,
        )
        released = current if approved else None
        if released:
            builder.add("release", "artifact_released", task_id=task.task_id, patch_hash=current.patch_hash)
        outcome = _outcome(
            scenario=scenario,
            task=task,
            expected_release=False,
            released=released,
            tested=current,
            reviewed=current,
            approval_test_passed=False if approved else None,
        )

    else:  # recovery
        initial = task.failing
        _emit_patch(builder, task, initial, cycle=0)
        _emit_test(builder, task, actual=initial, reported=initial, passed=False, cycle=0)
        failure_step = builder.add(
            "tester",
            "failure_detected",
            task_id=task.task_id,
            cycle=1,
            patch_hash=initial.patch_hash,
        )
        if RECOVERY_OBSERVATION_HOOK in enabled:
            fresh_step = _emit_observation(builder, task, cycle=1, fresh=True)
        else:
            _emit_observation(builder, task, cycle=1, fresh=False)
            builder.add("system", "recovery_wait", task_id=task.task_id, cycle=1, tick=1)
            builder.add("system", "recovery_wait", task_id=task.task_id, cycle=1, tick=2)
            builder.add("system", "recovery_wait", task_id=task.task_id, cycle=1, tick=3)
            fresh_step = _emit_observation(builder, task, cycle=1, fresh=True)
        recovered = task.good
        _emit_patch(builder, task, recovered, cycle=1)
        _emit_test(builder, task, actual=recovered, reported=recovered, passed=True, cycle=1)
        _emit_review(
            builder,
            task,
            inspected=recovered,
            decided=recovered,
            approved=True,
            cycle=1,
            enabled_hooks=enabled,
        )
        builder.add("release", "artifact_released", task_id=task.task_id, patch_hash=recovered.patch_hash)
        outcome = _outcome(
            scenario=scenario,
            task=task,
            expected_release=True,
            released=recovered,
            tested=recovered,
            reviewed=recovered,
            approval_test_passed=True,
            recovery_required=True,
            failure_step=failure_step,
            fresh_observation_step=fresh_step,
        )

    return WorkflowRun(builder.trace(), outcome)


def run_intervention(hook: str, arm: str, seed: int) -> WorkflowRun:
    if hook not in ALL_HOOKS:
        raise ValueError(f"unsupported workflow hook: {hook}")
    if arm not in {"active", "sham"}:
        raise ValueError("intervention arm must be active or sham")
    enabled = ALL_HOOKS - {hook} if arm == "active" else ALL_HOOKS
    return run_scenario(
        HOOK_SCENARIOS[hook],
        seed,
        enabled_hooks=enabled,
        arm=arm,
        intervention_hook=hook,
    )
