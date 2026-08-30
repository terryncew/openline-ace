from __future__ import annotations

import hashlib
from typing import Iterable

SCHEMA = "openline.ace.intervention-outcome.v2"
ACTIONS = (
    "CONTINUE",
    "LATERAL_LEFT",
    "LATERAL_RIGHT",
    "RETREAT",
    "SLOW",
    "STOP",
)
LAGS = (0, 40, 80, 120, 160)
CONTEXTS = 50
TARGET_SHA256 = hashlib.sha256(b"is002-reference-recovery-target").hexdigest()
CONSTRAINT_SHA256 = hashlib.sha256(b"is002-reference-constraints").hexdigest()
MODEL_VALIDATION_SHA256 = hashlib.sha256(
    b"is002-reference-model-validation"
).hexdigest()


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _row(
    *,
    dataset_id: str,
    evidence_mode: str,
    context_id: str,
    risk_bucket: str,
    action: str,
    lag_ms: int,
    replicate: int,
    success: bool,
) -> dict:
    row = {
        "schema": SCHEMA,
        "dataset_id": dataset_id,
        "evidence_mode": evidence_mode,
        "context_id": context_id,
        "snapshot_sha256": _hash(f"{dataset_id}:{context_id}:snapshot"),
        "apparent_risk_bucket": risk_bucket,
        "action_id": action,
        "lag_ms": lag_ms,
        "replicate": replicate,
        "trial_id": (
            f"{dataset_id}:{context_id}:{action}:{lag_ms}:{replicate}"
        ),
        "target_sha256": TARGET_SHA256,
        "constraint_set_sha256": CONSTRAINT_SHA256,
        "policy_authority": "NONE",
    }
    if evidence_mode == "validated_dynamics_model":
        row["success_probability"] = 1.0 if success else 0.0
        row["model_validation_receipt_sha256"] = MODEL_VALIDATION_SHA256
    else:
        row["outcome_success"] = success
    return row


def deterministic_global_control() -> list[dict]:
    """Complete deterministic grid where one global action always dominates."""
    rows: list[dict] = []
    dataset_id = "is002-deterministic-global-control"
    for index in range(CONTEXTS):
        context_id = f"global-{index:03d}"
        risk_bucket = f"risk-{index // 2:02d}"
        for action in ACTIONS:
            for lag in LAGS:
                success = action == "STOP" and lag <= 80
                rows.append(
                    _row(
                        dataset_id=dataset_id,
                        evidence_mode="deterministic_rollout",
                        context_id=context_id,
                        risk_bucket=risk_bucket,
                        action=action,
                        lag_ms=lag,
                        replicate=0,
                        success=success,
                    )
                )
    return rows


def deterministic_state_specific_control() -> list[dict]:
    """Matched-risk pairs with complementary remedies and lag contraction."""
    rows: list[dict] = []
    dataset_id = "is002-deterministic-state-specific-control"
    first_half = set(ACTIONS[:3])
    second_half = set(ACTIONS[3:])
    for pair_index in range(CONTEXTS // 2):
        severity = pair_index % 5
        remedy_limit_ms = 160 - (40 * severity)
        for side in ("a", "b"):
            context_id = f"pair-{pair_index:02d}:{side}"
            remedies = first_half if side == "a" else second_half
            risk_bucket = f"load-{pair_index:02d}"
            for action in ACTIONS:
                for lag in LAGS:
                    success = action in remedies and lag <= remedy_limit_ms
                    rows.append(
                        _row(
                            dataset_id=dataset_id,
                            evidence_mode="deterministic_rollout",
                            context_id=context_id,
                            risk_bucket=risk_bucket,
                            action=action,
                            lag_ms=lag,
                            replicate=0,
                            success=success,
                        )
                    )
    return rows


def stochastic_state_specific_control() -> list[dict]:
    rows: list[dict] = []
    for source in deterministic_state_specific_control():
        for replicate in range(4):
            row = dict(source)
            row["dataset_id"] = "is002-stochastic-state-specific-control"
            row["evidence_mode"] = "stochastic_rollout"
            row["replicate"] = replicate
            row["trial_id"] = (
                f"{row['dataset_id']}:{row['context_id']}:{row['action_id']}:"
                f"{row['lag_ms']}:{replicate}"
            )
            rows.append(row)
    return rows


def validated_model_state_specific_control() -> list[dict]:
    rows: list[dict] = []
    for source in deterministic_state_specific_control():
        row = dict(source)
        row["dataset_id"] = "is002-validated-model-state-specific-control"
        row["evidence_mode"] = "validated_dynamics_model"
        row["success_probability"] = 1.0 if row.pop("outcome_success") else 0.0
        row["model_validation_receipt_sha256"] = MODEL_VALIDATION_SHA256
        row["trial_id"] = (
            f"{row['dataset_id']}:{row['context_id']}:{row['action_id']}:"
            f"{row['lag_ms']}:0"
        )
        rows.append(row)
    return rows


def canonical_rows(rows: Iterable[dict]) -> list[dict]:
    return sorted(
        rows,
        key=lambda row: (
            str(row["dataset_id"]),
            str(row["context_id"]),
            str(row["action_id"]),
            int(row["lag_ms"]),
            int(row["replicate"]),
            str(row["trial_id"]),
        ),
    )
