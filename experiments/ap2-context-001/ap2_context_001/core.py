from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Execution:
    amount_minor: int
    currency: str
    payee: str


def extract_amount_range(payload: Any) -> dict[str, Any]:
    """Read the AP2 payment.amount_range constraint from a verified model/dict."""
    data = payload.model_dump(exclude_none=True) if hasattr(payload, "model_dump") else dict(payload)
    constraints = data.get("constraints", [])
    for item in constraints:
        if hasattr(item, "model_dump"):
            item = item.model_dump(exclude_none=True)
        if item.get("type") == "payment.amount_range":
            return dict(item)
    raise ValueError("verified mandate has no payment.amount_range constraint")


def has_allowed_payees(payload: Any) -> bool:
    data = payload.model_dump(exclude_none=True) if hasattr(payload, "model_dump") else dict(payload)
    for item in data.get("constraints", []):
        if hasattr(item, "model_dump"):
            item = item.model_dump(exclude_none=True)
        if item.get("type") == "payment.allowed_payees":
            return True
    return False


def final_mandate_accepts(payload: Any, execution: Execution) -> bool:
    """Evaluate only the semantics present in the final verified AP2 mandate."""
    rng = extract_amount_range(payload)
    if execution.currency != rng["currency"]:
        return False
    if rng.get("min") is not None and execution.amount_minor < int(rng["min"]):
        return False
    if execution.amount_minor > int(rng["max"]):
        return False

    # AM1 deliberately omits payment.allowed_payees. With no signed restriction,
    # final-artifact-only evaluation has no payee mismatch to detect.
    data = payload.model_dump(exclude_none=True) if hasattr(payload, "model_dump") else dict(payload)
    for item in data.get("constraints", []):
        if hasattr(item, "model_dump"):
            item = item.model_dump(exclude_none=True)
        if item.get("type") == "payment.allowed_payees":
            allowed_ids = {
                x.get("id")
                for x in item.get("allowed", [])
                if isinstance(x, dict)
            }
            return execution.payee in allowed_ids
    return True


def classify(ap2_native_verified: bool, gate_disposition: str) -> str:
    if not ap2_native_verified:
        return "INVALID_EXTERNAL_SUBSTRATE_AP2_VERIFY_FAILED"
    if gate_disposition == "DENY":
        return "VALID_AP2_POISONED_CONTEXT_BLOCKED_BY_UNCHANGED_OPENLINE"
    if gate_disposition == "COMMIT":
        return "VALID_AP2_POISONED_CONTEXT_CROSSES_UNCHANGED_OPENLINE"
    return "INDETERMINATE_OPENLINE_EVIDENCE_INCOMPLETE"
