"""Execute active, matched-sham, and restoration arms through EnvHarness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from envharness import Action, ActionableEnv, Observation

from .canonical import canonical_digest
from .environment import (
    CodeRepairEnv,
    MANUFACTURED_OPERATORS,
    NATIVE_OPERATORS,
    stack_proposal,
    unwrap_base,
)
from .model import EpisodeOutcome, Proposal, QueryTranscript, Task


@dataclass
class _Trace:
    events: list[dict[str, Any]]

    def reset(self, observation: Observation) -> None:
        self.events.append({"event": "reset", "observation": observation.model_dump(mode="json")})

    def step(self, action: Action, observation: Observation, terminated: bool) -> None:
        self.events.append(
            {
                "action": action.model_dump(mode="json"),
                "event": "step",
                "observation": observation.model_dump(mode="json"),
                "terminated": terminated,
            }
        )


def _profile(proposal: Proposal) -> str:
    layers = set(proposal.layers)
    if layers & NATIVE_OPERATORS:
        return "native"
    if layers & MANUFACTURED_OPERATORS:
        return "imposed"
    return "nuisance"


def _initial_patch(task: Task, proposal: Proposal) -> str:
    return task.alternate_patch if _profile(proposal) == "native" else task.correct_patch


def _step(env: ActionableEnv, trace: _Trace, name: str, **kwargs: Any) -> Observation:
    action = Action(name=name, kwargs=kwargs)
    response = env.step(action)
    trace.step(action, response.observation, response.terminated)
    return response.observation


def _standard_agent(env: ActionableEnv, trace: _Trace, task: Task, agent: str) -> None:
    """Three separately implemented deterministic policies with equal semantics."""
    if agent == "direct-v1":
        observation = _step(env, trace, "run_tests")
        if not bool(observation.data.get("passed")):
            _step(env, trace, "apply_patch", patch=task.correct_patch)
            _step(env, trace, "run_tests")
        _step(env, trace, "submit")
        return
    if agent == "ledger-v2":
        ledger: list[tuple[str, Observation]] = []
        ledger.append(("run_tests", _step(env, trace, "run_tests")))
        if not bool(ledger[-1][1].data.get("passed")):
            ledger.append(("apply_patch", _step(env, trace, "apply_patch", patch=task.correct_patch)))
            ledger.append(("run_tests", _step(env, trace, "run_tests")))
        ledger.append(("submit", _step(env, trace, "submit")))
        return
    if agent == "queue-v2":
        queue: list[tuple[str, dict[str, Any]]] = [("run_tests", {})]
        while queue:
            name, kwargs = queue.pop(0)
            observation = _step(env, trace, name, **kwargs)
            if name == "run_tests":
                if bool(observation.data.get("passed")):
                    queue.append(("submit", {}))
                else:
                    queue.extend(
                        [
                            ("apply_patch", {"patch": task.correct_patch}),
                            ("run_tests", {}),
                        ]
                    )
        return
    raise ValueError(f"unknown agent implementation: {agent}")


def _direct_submit(env: ActionableEnv, trace: _Trace, agent: str) -> None:
    if agent == "queue-v2":
        queue = [("submit", {})]
        while queue:
            name, kwargs = queue.pop(0)
            _step(env, trace, name, **kwargs)
    elif agent in {"direct-v1", "ledger-v2"}:
        _step(env, trace, "submit")
    else:
        raise ValueError(f"unknown agent implementation: {agent}")


def _restoration_agent(
    env: ActionableEnv,
    trace: _Trace,
    task: Task,
    profile: str,
    agent: str,
) -> int:
    if profile == "native":
        # Observe the break once, then perform the frozen recovery sequence.
        _step(env, trace, "run_tests")
        observation = _step(env, trace, "run_tests")
        if bool(observation.data.get("passed")):
            raise RuntimeError("restoration failed to obtain an independent observation")
        _step(env, trace, "apply_patch", patch=task.correct_patch)
        final_test = _step(env, trace, "run_tests")
        if not bool(final_test.data.get("passed")):
            raise RuntimeError("restoration failed to validate corrected patch")
        _step(env, trace, "submit")
        return 4
    if profile == "imposed":
        _step(env, trace, "run_tests")
        _step(env, trace, "submit")
        return 2
    _direct_submit(env, trace, agent)
    return 0


def run_arm(
    proposal: Proposal,
    task: Task,
    agent: str,
    arm: str,
) -> EpisodeOutcome:
    profile = _profile(proposal)
    base = CodeRepairEnv(task=task, initial_patch=_initial_patch(task, proposal))
    env = stack_proposal(base, proposal, arm)
    trace = _Trace([])
    reset = env.reset(seed=task.nuisance_seed)
    trace.reset(reset.observation)
    recovery_horizon: int | None = None
    if arm == "restoration":
        recovery_horizon = _restoration_agent(env, trace, task, profile, agent)
    elif profile == "imposed":
        _direct_submit(env, trace, agent)
    else:
        _standard_agent(env, trace, task, agent)
    unwrapped = unwrap_base(env)
    evaluation = unwrapped.evaluate()  # Only the original verifier is authoritative.
    energy = proposal.sham_energy if arm == "sham" else proposal.active_energy
    trace.events.append(
        {
            "artifact_valid": bool(evaluation.metrics["artifact_valid"]),
            "event": "original_verifier",
            "success": evaluation.success,
        }
    )
    return EpisodeOutcome(
        arm=arm,
        external_success=evaluation.success,
        artifact_valid=bool(evaluation.metrics["artifact_valid"]),
        submitted=bool(evaluation.metrics["submitted"]),
        action_count=sum(item["event"] == "step" for item in trace.events),
        recovery_horizon=recovery_horizon,
        trace_digest=canonical_digest(trace.events),
        energy=energy,
    )


def execute_queries(
    proposal: Proposal,
    task: Task,
    agent: str,
) -> QueryTranscript:
    transcript = QueryTranscript(
        active=run_arm(proposal, task, agent, "active"),
        sham=run_arm(proposal, task, agent, "sham"),
        restoration=run_arm(proposal, task, agent, "restoration"),
    )
    if transcript.active.energy != transcript.sham.energy or transcript.query_count != 3:
        raise RuntimeError("intervention budget boundary failed")
    return transcript
