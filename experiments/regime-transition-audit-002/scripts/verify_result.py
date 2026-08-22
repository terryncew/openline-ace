from pathlib import Path
import json, hashlib, sys
ROOT=Path(__file__).resolve().parents[1]
required=["source_manifest.json","preregistration.json","external_raw.json","external_cases.jsonl","external_result.json"]
missing=[x for x in required if not (ROOT/x).exists()]
if missing:
    print(json.dumps({"verified":False,"missing":missing},indent=2)); raise SystemExit(2)
r=json.loads((ROOT/"external_result.json").read_text())
checks={
 "policy_authority_none":r.get("policy_authority")=="NONE",
 "allowed_verdict":r.get("verdict") in {"PREDICTIVE_ADVANTAGE_CANDIDATE","NO_PREDICTIVE_ADVANTAGE","DATA_INSUFFICIENT"},
 "source_hash":r.get("source_manifest_sha256")==hashlib.sha256((ROOT/"source_manifest.json").read_bytes()).hexdigest(),
 "prereg_hash":r.get("preregistration_sha256")==hashlib.sha256((ROOT/"preregistration.json").read_bytes()).hexdigest(),
 "raw_hash":r.get("external_raw_sha256")==hashlib.sha256((ROOT/"external_raw.json").read_bytes()).hexdigest(),
 "cases_hash":r.get("external_cases_sha256")==hashlib.sha256((ROOT/"external_cases.jsonl").read_bytes()).hexdigest(),
}
out={"schema":"openline.ace.rta002.independent_verification.v1","verified":all(checks.values()),"checks":checks,"verdict":r.get("verdict"),"policy_authority":"NONE"}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
