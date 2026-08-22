
from pathlib import Path
import json,hashlib,sys
R=Path(__file__).resolve().parents[1]
res=json.loads((R/"external_result.json").read_text())
checks={"authority_none":res.get("policy_authority")=="NONE",
"allowed_verdict":res.get("verdict") in {"PREDICTIVE_ADVANTAGE_CANDIDATE","NO_PREDICTIVE_ADVANTAGE","DATA_INSUFFICIENT"}}
for n in ["source_manifest","preregistration","external_raw","external_cases"]:
    f=R/(n+".json" if n not in {"external_cases"} else "external_cases.jsonl")
    checks[n+"_hash"]=res.get(n+"_sha256")==hashlib.sha256(f.read_bytes()).hexdigest()
out={"schema":"openline.ace.rta003.verification.v1","verified":all(checks.values()),"checks":checks,"verdict":res.get("verdict"),"policy_authority":"NONE"}
print(json.dumps(out,indent=2,sort_keys=True)); raise SystemExit(0 if out["verified"] else 2)
