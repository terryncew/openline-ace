from __future__ import annotations

import uuid
from dataclasses import replace
from typing import Any

from .canonical import sha256
from .crypto import SignerRegistry
from .model import Receipt


def issue_receipt(
    registry: SignerRegistry,
    *,
    issuer_id: str,
    kind: str,
    subject_id: str,
    subject_sha256: str,
    issued_at: int,
    expires_at: int | None,
    standing: str = "ACTIVE",
    claims: dict[str, Any] | None = None,
    dependencies: tuple[str, ...] = (),
) -> Receipt:
    role = registry.role(issuer_id)
    if role is None:
        raise KeyError(issuer_id)
    base = Receipt(
        receipt_id=str(uuid.uuid4()),
        kind=kind,
        issuer_id=issuer_id,
        issuer_role=role,
        subject_id=subject_id,
        subject_sha256=subject_sha256,
        issued_at=issued_at,
        expires_at=expires_at,
        standing=standing,
        claims=claims or {},
        dependencies=dependencies,
        signature="",
    )
    return registry.sign(issuer_id, base)


def receipt_fingerprint(receipt: Receipt) -> str:
    return sha256(replace(receipt, signature=""))
