from __future__ import annotations

from typing import Any, Iterable

from .schemas import assert_blind


def make_proposer_packet(traces: Iterable[dict[str, Any]]) -> dict[str, Any]:
    public = []
    for i, trace in enumerate(traces):
        tool = trace.get("tool_observation") or {}
        public.append({
            "trace_id": str(trace.get("trace_id", f"trace-{i:04d}")),
            "task_id": str(trace.get("task_id", "unknown")),
            "events": list(trace.get("events", [])),
            "tool_observation": {
                "value": str(tool.get("value", "")),
                "marker": str(tool.get("marker", "")),
                "padding": str(tool.get("padding", "")),
            },
            "final_success": bool(trace.get("final_success", True)),
        })
    packet = {
        "protocol": "openline.agent-contract-audit.proposer-packet.v2",
        "authority": "NONE",
        "task_description": "An agent reads a three-field ticket and returns the ticket value.",
        "tool_schema": {"read_ticket": {"returns": ["value", "marker", "padding"]}},
        "successful_baseline_traces": public,
        "instruction": (
            "Propose 2-4 plausible relational dependencies visible in these successful traces. "
            "Include suspicious always-present fields or steps as candidates rather than deciding necessity. "
            "Do not infer or request hidden verifier logic."
        ),
    }
    assert_blind(packet)
    return packet


def make_compiler_packet(candidates: list[dict[str, Any]], surface_catalog: dict[str, Any]) -> dict[str, Any]:
    packet = {
        "protocol": "openline.agent-contract-audit.compiler-packet.v1",
        "authority": "NONE",
        "candidates": candidates,
        "surfaces": [
            {"surface_id": s["surface_id"], "public_description": s["public_description"]}
            for s in surface_catalog["surfaces"]
        ],
        "instruction": (
            "Map each candidate to the closest public intervention surface. "
            "Mapping chooses what to test; it does not decide standing."
        ),
    }
    assert_blind(packet)
    return packet
