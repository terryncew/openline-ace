from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .canonical import sha256_bytes


def _bounded(value: Any, limit: int = 240) -> Any:
    if isinstance(value, str):
        return value[:limit]
    if isinstance(value, (int, bool)) or value is None:
        return value
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, list):
        return [_bounded(v, limit) for v in value[:32]]
    if isinstance(value, dict):
        return {str(k): _bounded(v, limit) for k, v in list(value.items())[:32]}
    return str(value)[:limit]


def build_proposer_packet(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    parsed = json.loads(raw.decode("utf-8"))
    spans: list[dict[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if "name" in value and (
                "spanId" in value or "span_id" in value or "attributes" in value or "events" in value
            ):
                spans.append({
                    "name": str(value.get("name", ""))[:200],
                    "span_id": value.get("spanId", value.get("span_id")),
                    "parent_span_id": value.get("parentSpanId", value.get("parent_span_id")),
                    "attributes": _bounded(value.get("attributes", {})),
                    "events": _bounded(value.get("events", [])),
                    "status": _bounded(value.get("status", {})),
                })
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(parsed)
    return {
        "protocol": "openline.agent-contract-audit.proposer-packet.v1",
        "trace_sha256": sha256_bytes(raw),
        "trace_format": "otlp-json-or-compatible",
        "span_count": len(spans),
        "spans": spans[:512],
        "proposer_authority": "NONE",
        "instructions": [
            "Propose candidate load-bearing relationships, not standings.",
            "Do not include artifact_valid, ground truth, verdict, or expected standing.",
            "Each candidate must define active, matched sham, and restoration interventions.",
        ],
    }
