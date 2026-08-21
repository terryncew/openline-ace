from __future__ import annotations
import hashlib, json
from pathlib import Path
from .fixtures import AgentWorkflowAdapter, DistributedSystemAdapter, ControlSimulationAdapter
from .protocol import audit_adapter

PROFILE = "openline.ace.cross-substrate-conformance.v1"
BASE_COMMIT = "630919721a6d27b62f7397ec891e1027ede44831"

def all_records():
    adapters = (AgentWorkflowAdapter(), DistributedSystemAdapter(), ControlSimulationAdapter())
    return tuple(r for adapter in adapters for r in audit_adapter(adapter))

def build_result():
    records = all_records()
    supported = {r.candidate.candidate_id for r in records if r.grade.standing == "SUPPORTED"}
    rituals = {r.candidate.candidate_id for r in records if r.grade.standing == "REJECTED_RITUAL"}
    undecidable = [r for r in records if r.grade.standing == "UNDECIDABLE"]
    expected_supported = {"fresh-test-binding", "majority-before-commit", "fresh-sensor-feedback"}
    expected_rituals = {"planning-marker", "leader-audit-marker", "telemetry-marker"}
    passed = supported == expected_supported and rituals == expected_rituals and not undecidable
    return {
        "profile": PROFILE,
        "base_commit": BASE_COMMIT,
        "status": "CROSS_SUBSTRATE_CONFORMANCE_PASS" if passed else "CROSS_SUBSTRATE_CONFORMANCE_FAIL",
        "scientific_claim": "One frozen active/sham/restoration grader separates planted load-bearing dependencies from perfect observational rituals across three heterogeneous conformance fixtures.",
        "claim_boundary": [
            "Conformance demonstration only; not external discovery evidence.",
            "Control specimen is simulation only; no physical robotics claim.",
            "Distributed specimen is a deterministic safety model; not a production cluster.",
            "No universal mechanism or cross-domain law is claimed.",
            "No policy authority or runtime permission is created."
        ],
        "supported_count": len(supported),
        "ritual_rejected_count": len(rituals),
        "undecidable_count": len(undecidable),
        "candidate_count": len(records),
        "policy_authority": "NONE",
        "runtime_permission": "NONE",
        "records": [r.to_dict() for r in records],
    }

def canonical_bytes(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()

def write_evidence(path: Path):
    result = build_result()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    receipt = {
        "profile": "openline.ace.cross-substrate-conformance-receipt.v1",
        "result_sha256": hashlib.sha256(canonical_bytes(result)).hexdigest(),
        "status": result["status"],
        "policy_authority": "NONE",
        "runtime_permission": "NONE",
    }
    path.with_name("receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    return result
