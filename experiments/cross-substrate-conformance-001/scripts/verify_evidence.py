import hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def canonical(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
result = json.loads((ROOT/"evidence/result.json").read_text())
receipt = json.loads((ROOT/"evidence/receipt.json").read_text())
assert receipt["result_sha256"] == hashlib.sha256(canonical(result)).hexdigest()
assert result["status"] == "CROSS_SUBSTRATE_CONFORMANCE_PASS"
assert (result["supported_count"], result["ritual_rejected_count"], result["undecidable_count"]) == (3,3,0)
assert result["policy_authority"] == receipt["policy_authority"] == "NONE"
assert result["runtime_permission"] == receipt["runtime_permission"] == "NONE"
print("cross_substrate_evidence_verified")
