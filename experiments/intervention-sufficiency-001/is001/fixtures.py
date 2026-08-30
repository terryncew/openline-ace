from __future__ import annotations

import hashlib
from typing import Iterable

SCHEMA = "openline.ace.intervention-outcome.v1"
ACTIONS = ("counter_left", "hold", "counter_right")
LAGS = (0, 40, 80, 120, 160)
REPLICATES = 4
TARGET_SHA256 = hashlib.sha256(
    b"is001-reference-upright-corridor-target-v1"
).hexdigest()


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _row(
    dataset_id: str,
    context_id: str,
    risk_bucket: str,
    action: str,
    lag_ms: int,
    replicate: int,
    recovered: bool,
) -> dict:
    return {
        "schema": SCHEMA,
        "dataset_id": dataset_id,
        "context_id": context_id,
        "snapshot_sha256": _hash(f"{dataset_id}:{context_id}:snapshot"),
        "apparent_risk_bucket": risk_bucket,
        "action_id": action,
        "lag_ms": lag_ms,
        "replicate": replicate,
        "trial_id": f"{dataset_id}:{context_id}:{action}:{lag_ms}:{replicate}",
        "recovered": recovered,
        "target_sha256": TARGET_SHA256,
        "policy_authority": "NONE",
    }


def global_rule_control() -> list[dict]:
    """Complete grid where HOLD is the same remedy for every state."""
    rows: list[dict] = []
    dataset_id = "global-rule-control"
    for severity in range(6):
        for direction in ("left", "right"):
            context_id = f"severity-{severity}:{direction}"
            for action in ACTIONS:
                for lag in LAGS:
                    recovered = action == "hold" and lag <= 80
                    for replicate in range(REPLICATES):
                        rows.append(
                            _row(
                                dataset_id,
                                context_id,
                                f"severity-{severity}",
                                action,
                                lag,
                                replicate,
                                recovered,
                            )
                        )
    return rows


def state_specific_control() -> list[dict]:
    """Matched-risk mirror states with opposite remedies and lag contraction."""
    rows: list[dict] = []
    dataset_id = "state-specific-control"
    for severity in range(6):
        remedy_limit_ms = 120 - 20 * severity
        for direction in ("left", "right"):
            context_id = f"severity-{severity}:{direction}"
            required = "counter_right" if direction == "left" else "counter_left"
            for action in ACTIONS:
                for lag in LAGS:
                    directional_recovery = action == required and lag <= remedy_limit_ms
                    mild_hold = action == "hold" and severity < 2 and lag <= 40
                    recovered = directional_recovery or mild_hold
                    for replicate in range(REPLICATES):
                        rows.append(
                            _row(
                                dataset_id,
                                context_id,
                                f"severity-{severity}",
                                action,
                                lag,
                                replicate,
                                recovered,
                            )
                        )
    return rows


def canonical_rows(rows: Iterable[dict]) -> list[dict]:
    return sorted(
        rows,
        key=lambda r: (
            r["dataset_id"],
            r["context_id"],
            r["action_id"],
            int(r["lag_ms"]),
            int(r["replicate"]),
            r["trial_id"],
        ),
    )
