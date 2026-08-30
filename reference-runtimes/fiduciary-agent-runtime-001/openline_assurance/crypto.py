from __future__ import annotations

import hashlib
import hmac
from dataclasses import replace
from typing import Mapping

from .canonical import canonical_bytes
from .model import Receipt


class SignerRegistry:
    """Reference verifier registry.

    Uses HMAC only to keep the reference runtime dependency-free. Production
    adapters should replace this with hardware-backed or asymmetric keys. The
    important invariant exercised here is role/key separation, not HMAC as a
    production trust model.
    """

    def __init__(self, secrets: Mapping[str, bytes], roles: Mapping[str, str]):
        self._secrets = dict(secrets)
        self._roles = dict(roles)

    def role(self, issuer_id: str) -> str | None:
        return self._roles.get(issuer_id)

    def sign(self, issuer_id: str, receipt: Receipt) -> Receipt:
        if issuer_id not in self._secrets:
            raise KeyError(f"unknown signer: {issuer_id}")
        if receipt.issuer_id != issuer_id:
            raise ValueError("receipt issuer does not match signing key")
        expected_role = self._roles[issuer_id]
        if receipt.issuer_role != expected_role:
            raise ValueError("receipt issuer role does not match registry")
        unsigned = replace(receipt, signature="")
        sig = hmac.new(self._secrets[issuer_id], canonical_bytes(unsigned), hashlib.sha256).hexdigest()
        return replace(receipt, signature=sig)

    def verify(self, receipt: Receipt) -> bool:
        secret = self._secrets.get(receipt.issuer_id)
        if secret is None:
            return False
        if self._roles.get(receipt.issuer_id) != receipt.issuer_role:
            return False
        unsigned = replace(receipt, signature="")
        expected = hmac.new(secret, canonical_bytes(unsigned), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, receipt.signature)
