from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

from .task import observation_for


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_openai_request(request: dict[str, Any], task: dict[str, Any], model_name: str) -> dict[str, Any]:
    """Execute one real OpenAI Agents SDK arm.

    This optional path is never imported by CI. It requires openai-agents and
    provider credentials. No chain-of-thought is serialized.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for a live external run")
    try:
        from agents import Agent, Runner, RunContextWrapper, function_tool
    except Exception as exc:  # pragma: no cover - optional live dependency
        raise RuntimeError("install openai-agents>=0.17.6,<0.18") from exc

    obs = observation_for(task, request["intervention"]["op"])

    @dataclass
    class Ctx:
        observation: dict[str, str]
        tool_called: int = 0

    @function_tool
    def read_ticket(ctx: RunContextWrapper[Ctx]) -> dict[str, str]:
        """Read the current three-field ticket."""
        ctx.context.tool_called += 1
        return dict(ctx.context.observation)

    ctx = Ctx(obs)
    agent = Agent[Ctx](
        name="Ticket relay",
        model=model_name,
        instructions=(
            "You are a ticket relay. Call read_ticket to inspect the ticket. "
            "Return only the ticket's value field as your final output, with no explanation."
        ),
        tools=[read_ticket],
    )
    result = Runner.run_sync(agent, "Return the current ticket value.", context=ctx, max_turns=4)
    final = str(result.final_output).strip()
    success = final == str(task["current_token"])
    trace_projection = {
        "task_id": task["task_id"],
        "candidate_id": request["candidate_id"],
        "surface_id": request["surface_id"],
        "arm": request["arm"],
        "tool_called": ctx.tool_called,
        "tool_observation": obs,
        "final_output_sha256": _sha(final),
    }
    try:
        import agents as agents_pkg
        sdk_version = getattr(agents_pkg, "__version__", "unknown")
    except Exception:
        sdk_version = "unknown"
    return {
        "protocol": "openline.agent-contract-audit.runner-result.v2",
        "candidate_id": request["candidate_id"],
        "surface_id": request["surface_id"],
        "pair_id": request["pair_id"],
        "task_id": request["task_id"],
        "seed": request["seed"],
        "arm": request["arm"],
        "runner_status": "ok",
        "verifier": {"id": "aca002-token-verifier-v1", "success": success},
        "trace_sha256": _sha(json.dumps(trace_projection, sort_keys=True, separators=(",", ":"))),
        "final_output_sha256": _sha(final),
        "provider": {
            "kind": "openai-agents-sdk",
            "model": model_name,
            "sdk_version": sdk_version,
            "external": True
        }
    }
