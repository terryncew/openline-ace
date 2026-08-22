from __future__ import annotations

from .canonical import object_hash
from .model import StateSnapshot, VerifiedBaseline


def mint_baseline(
    *,
    verified_at: str,
    max_age_seconds: int,
    control_plane: dict[str, object],
    domain: dict[str, object],
    support_standing: str = "STANDING",
    parent_receipt_id: str | None = None,
) -> VerifiedBaseline:
    body = {
        "profile": "openline.verified-reference-baseline.v1",
        "parent_receipt_id": parent_receipt_id,
        "verified_at": verified_at,
        "max_age_seconds": max_age_seconds,
        "support_standing": support_standing,
        "control_plane": dict(control_plane),
        "domain": dict(domain),
        "policy_authority": "NONE",
        "runtime_permission": "NONE",
    }
    receipt_id = "sv-" + object_hash(body)[:24]
    return VerifiedBaseline(
        receipt_id=receipt_id,
        parent_receipt_id=parent_receipt_id,
        verified_at=verified_at,
        max_age_seconds=max_age_seconds,
        support_standing=support_standing,
        control_plane=dict(control_plane),
        domain=dict(domain),
    )


def mint_successor_baseline(
    *,
    previous: VerifiedBaseline,
    verified_state: StateSnapshot,
    verified_at: str,
    max_age_seconds: int | None = None,
) -> VerifiedBaseline:
    return mint_baseline(
        verified_at=verified_at,
        max_age_seconds=(
            previous.max_age_seconds
            if max_age_seconds is None
            else max_age_seconds
        ),
        control_plane=dict(verified_state.control_plane),
        domain=dict(verified_state.domain),
        support_standing="STANDING",
        parent_receipt_id=previous.receipt_id,
    )
