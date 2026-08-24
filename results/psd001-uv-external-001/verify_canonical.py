from pathlib import Path
import hashlib, json, sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EXP = REPO / "experiments" / "prospective-selective-standing-001"
sys.path.insert(0, str(EXP))
from psd001.core import adjudicate

def hfile(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",",":"), ensure_ascii=False).encode()

receipt = json.loads((HERE/"CANONICAL_RECEIPT.json").read_text())
saved = receipt["receipt_sha256"]
body = dict(receipt)
body.pop("receipt_sha256")
receipt_hash_ok = hashlib.sha256(canon(body)).hexdigest() == saved

hash_checks = {
    name: hfile(HERE/name) == digest
    for name, digest in receipt["preserved_evidence_sha256"].items()
}

external = json.loads((HERE/"external_result.json").read_text())
prereg = json.loads((HERE/"preregistration.json").read_text())
t0 = json.loads((HERE/"t0_model.json").read_text())
interventions = json.loads((HERE/"interventions.json").read_text())
traces = [json.loads(line) for line in (HERE/"external_traces.jsonl").read_text().splitlines() if line.strip()]

recomputed = adjudicate(t0, traces, interventions["pool"], prereg)

checks = {
    "receipt_hash": receipt_hash_ok,
    "all_evidence_hashes": all(hash_checks.values()),
    "verdict_recomputed": recomputed["verdict"] == external["verdict"] == receipt["result"]["verdict"],
    "openline_recall": recomputed["metrics"]["openline_evidence_graph"]["decision_recall"] == receipt["result"]["openline"]["recall"],
    "openline_precision": recomputed["metrics"]["openline_evidence_graph"]["decision_precision"] == receipt["result"]["openline"]["precision"],
    "openline_false_reopen_rate": recomputed["metrics"]["openline_evidence_graph"]["false_reopen_rate"] == receipt["result"]["openline"]["false_reopen_rate"],
    "artifact_precision": recomputed["metrics"]["artifact_component_join"]["decision_precision"] == receipt["result"]["artifact_component_join"]["precision"],
    "artifact_false_reopen_rate": recomputed["metrics"]["artifact_component_join"]["false_reopen_rate"] == receipt["result"]["artifact_component_join"]["false_reopen_rate"],
    "equivalence_mismatches": recomputed["equivalence_mismatches"] == 0 == receipt["result"]["equivalence_mismatches"],
    "missing_edge_safety": recomputed["missing_edge_safety"]["silent_false_retain_count"] == 0,
    "policy_authority_none": receipt["policy_authority"] == "NONE",
    "runtime_permission_none": receipt["runtime_permission"] == "NONE",
    "signature_boundary": receipt["signature_status"] == "HASH_BOUND_ONLY",
}

out = {
    "schema":"openline.ace.psd001.canonical-verification.v1",
    "verified": all(checks.values()),
    "checks": checks,
    "evidence_hash_checks": hash_checks,
    "recomputed_verdict": recomputed["verdict"],
    "receipt_sha256": saved,
}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
