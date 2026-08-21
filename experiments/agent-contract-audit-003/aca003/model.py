from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping

ELIGIBLE_SOURCE_STATUS = "BLIND_EXTERNAL_RUN_COMPLETED"
ELIGIBLE_VERIFICATION_STATUS = "PASS"

@dataclass(frozen=True)
class Eligibility:
    eligible: bool
    reasons: tuple[str, ...]

def check_source_packet(packet: Mapping[str, Any]) -> Eligibility:
    reasons: list[str] = []
    if packet.get("protocol") != "openline.agent-contract-audit.external-result.v1":
        reasons.append("wrong_source_protocol")
    if packet.get("run_status") != ELIGIBLE_SOURCE_STATUS:
        reasons.append("external_run_not_completed")
    verification = packet.get("independent_verification")
    if not isinstance(verification, dict) or verification.get("status") != ELIGIBLE_VERIFICATION_STATUS:
        reasons.append("independent_verification_not_passed")
    if packet.get("policy_authority") not in (None, "NONE"):
        reasons.append("source_claims_policy_authority")
    grade = packet.get("grade")
    if not isinstance(grade, dict) or grade.get("standing") != "SUPPORTED":
        reasons.append("standing_not_supported")
    if isinstance(grade, dict):
        pairs = grade.get("pairs")
        if type(pairs) is not int or pairs < 64:
            reasons.append("insufficient_pairs")
    for key in ("pre_intervention_seal_sha256","results_sha256","independent_verification_sha256"):
        value = packet.get(key)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            reasons.append(f"invalid_{key}")
    return Eligibility(not reasons, tuple(sorted(reasons)))

def micros(value: Any) -> int:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("metric must be numeric")
    out = round(float(value) * 1_000_000)
    if not -9007199254740991 <= out <= 9007199254740991:
        raise ValueError("metric micros out of range")
    return int(out)
