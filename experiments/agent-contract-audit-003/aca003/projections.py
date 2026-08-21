from __future__ import annotations
from typing import Any, Mapping
from .canonical import object_hash

def claim_graph_projection(receipt: Mapping[str, Any], disclosure: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "profile":"openline.contract-standing.claim-graph-projection.v1",
        "candidate_relation":{
            "relation_id":"contract:"+disclosure["candidate_id"],
            "relation_text":disclosure["contract_text"],
            "scope":disclosure["scope"],
            "source_receipt_hash":receipt["payload_hash"],
            "standing":"SUPPORTED",
            "admission_status":"UNADMITTED",
        },
        "receiver_policy_required":True,
        "policy_authority":"NONE",
        "projection_hash_basis":object_hash({"receipt":receipt["payload_hash"],"disclosure":receipt["disclosure_sha256"]}),
    }

def receipt_gate_projection(receipt: Mapping[str, Any], disclosure: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "profile":"openline.contract-standing.receipt-gate-evidence.v1",
        "evidence_type":"causal_contract_standing",
        "candidate_id":disclosure["candidate_id"],
        "standing_receipt_hash":receipt["payload_hash"],
        "source_results_sha256":disclosure["results_sha256"],
        "evidence_only":True,
        "requested_disposition":None,
        "commit_authorization":None,
        "runtime_permission":"NONE",
        "policy_authority":"NONE",
        "receiver_reverification_required":True,
    }
