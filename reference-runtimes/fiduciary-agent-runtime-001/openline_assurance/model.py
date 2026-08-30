from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Disposition(str, Enum):
    COMMIT = "COMMIT"
    QUARANTINE = "QUARANTINE"
    DENY = "DENY"


class Standing(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    actor_id: str
    action: str
    target: str
    payload_sha256: str
    changed_paths: tuple[str, ...] = ()
    mutation_tier: str = "TIER1_OPERATIONAL"
    generator_surface: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Receipt:
    receipt_id: str
    kind: str
    issuer_id: str
    issuer_role: str
    subject_id: str
    subject_sha256: str
    issued_at: int
    expires_at: int | None
    standing: str
    claims: dict[str, Any]
    dependencies: tuple[str, ...]
    signature: str


@dataclass(frozen=True)
class GateDecision:
    decision_id: str
    proposal_id: str
    disposition: str
    reasons: tuple[str, ...]
    relied_on_receipts: tuple[str, ...]
    receipt_id: str | None = None


@dataclass(frozen=True)
class ReopenEvent:
    cause_receipt_id: str
    reopened_decision_ids: tuple[str, ...]
    reopened_receipt_ids: tuple[str, ...]
