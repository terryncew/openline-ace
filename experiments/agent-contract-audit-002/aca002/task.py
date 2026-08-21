from __future__ import annotations

import hashlib
from typing import Any


def _substitute(value: str, label: str) -> str:
    digest = hashlib.sha256(label.encode("utf-8")).hexdigest().upper()
    return (digest * ((len(value) // len(digest)) + 1))[: len(value)]


def observation_for(task: dict[str, Any], op: str) -> dict[str, str]:
    value = str(task["current_token"])
    marker = str(task["audit_marker"])
    padding = str(task["padding"])
    if op == "none" or op == "ticket_token_current" or op == "audit_marker_restore" or op == "padding_restore":
        pass
    elif op == "ticket_token_stale":
        value = str(task["stale_token"])
    elif op == "audit_marker_neutralize":
        marker = "_" * len(marker)
    elif op == "audit_marker_substitute":
        marker = _substitute(marker, task["task_id"] + ":marker")
    elif op == "padding_neutralize":
        padding = "_" * len(padding)
    elif op == "padding_substitute":
        padding = _substitute(padding, task["task_id"] + ":padding")
    else:
        raise ValueError(f"unknown operation: {op}")
    return {"value": value, "marker": marker, "padding": padding}


def expected_token_hash(task: dict[str, Any]) -> str:
    return hashlib.sha256(str(task["current_token"]).encode("utf-8")).hexdigest()
