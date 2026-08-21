from __future__ import annotations
from typing import Any, Mapping
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from .canonical import canonical, sha256_hex
from .model import check_source_packet, micros

PROFILE_ID = "openline.contract-standing-receipt.v1"
CANON_ID = "olp-canonical-json-int-v1"
ALGO_ID = "aca003-standing-handoff-v1"

def _hex64(value: str, label: str) -> str:
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"invalid {label}")
    return value

def build_disclosure(packet: Mapping[str, Any]) -> dict[str, Any]:
    eligibility = check_source_packet(packet)
    if not eligibility.eligible:
        raise ValueError("source packet ineligible: " + ",".join(eligibility.reasons))
    grade = packet["grade"]
    delta = grade["active_minus_sham_failure_delta"]
    recovery = grade["restoration_minus_active_success_delta"]
    return {
        "profile": PROFILE_ID + ".disclosure",
        "candidate_id": str(packet["candidate"]["candidate_id"]),
        "contract_text": str(packet["candidate"]["text"]),
        "scope": packet["candidate"]["scope"],
        "source_experiment": str(packet.get("source_experiment", "agent-contract-audit-002")),
        "source_run_id": str(packet["run_id"]),
        "standing": "SUPPORTED",
        "pairs": int(grade["pairs"]),
        "active_minus_sham_failure_delta_micros":{
            "mean":micros(delta["mean"]),"ci_low":micros(delta["ci_low"]),"ci_high":micros(delta["ci_high"])
        },
        "restoration_minus_active_success_delta_micros":{
            "mean":micros(recovery["mean"]),"ci_low":micros(recovery["ci_low"]),"ci_high":micros(recovery["ci_high"])
        },
        "baseline_success_rate_micros": micros(grade["baseline_success_rate"]),
        "sham_failure_rate_micros": micros(grade["sham_failure_rate"]),
        "pre_intervention_seal_sha256": _hex64(packet["pre_intervention_seal_sha256"],"pre_intervention_seal_sha256"),
        "results_sha256": _hex64(packet["results_sha256"],"results_sha256"),
        "independent_verification_sha256": _hex64(packet["independent_verification_sha256"],"independent_verification_sha256"),
        "policy_authority":"NONE",
        "runtime_permission":"NONE",
        "receiver_admission_required":True,
    }

def sign_standing(packet: Mapping[str, Any], private_key_bytes: bytes):
    disclosure = build_disclosure(packet)
    disclosure_hash = sha256_hex(canonical(disclosure))
    body = {
        "kind":"contract_standing_receipt",
        "receipt_version":PROFILE_ID,
        "algorithm_id":ALGO_ID,
        "canonicalization_id":CANON_ID,
        "spec_uri":"docs/CONTRACT_STANDING_HANDOFF.md",
        "attestation":"self",
        "capture_status":"provisional",
        "candidate_id":disclosure["candidate_id"],
        "standing":"SUPPORTED",
        "source_experiment":disclosure["source_experiment"],
        "source_run_id":disclosure["source_run_id"],
        "source_results_sha256":disclosure["results_sha256"],
        "disclosure_sha256":disclosure_hash,
        "policy_authority":"NONE",
        "runtime_permission":"NONE",
        "receiver_admission_required":True,
    }
    body_bytes=canonical(body)
    key=Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    receipt=dict(body)
    receipt["payload_hash"]=sha256_hex(body_bytes)
    receipt["signature"]={
        "algorithm":"Ed25519",
        "public_key":key.public_key().public_bytes_raw().hex(),
        "value":key.sign(body_bytes).hex(),
    }
    return receipt, disclosure

def verify_receipt(receipt: Mapping[str, Any], disclosure: Mapping[str, Any]) -> None:
    body={k:v for k,v in receipt.items() if k not in {"payload_hash","signature"}}
    body_bytes=canonical(body)
    if receipt.get("payload_hash") != sha256_hex(body_bytes): raise ValueError("payload hash mismatch")
    if receipt.get("disclosure_sha256") != sha256_hex(canonical(disclosure)): raise ValueError("disclosure hash mismatch")
    sig=receipt.get("signature")
    if not isinstance(sig,dict) or sig.get("algorithm")!="Ed25519": raise ValueError("bad signature envelope")
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(sig["public_key"])).verify(bytes.fromhex(sig["value"]),body_bytes)
    if receipt.get("policy_authority")!="NONE" or receipt.get("runtime_permission")!="NONE":
        raise ValueError("authority escalation")
