from pathlib import Path
from hashlib import sha256
import json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from psd001.core import adjudicate
P=json.loads((ROOT/"preregistration.json").read_text())
r=json.loads((ROOT/"external_result.json").read_text())
allowed=set(P["allowed_verdicts"])
checks={
 "allowed_verdict":r.get("verdict") in allowed,
 "prereg_hash":r.get("preregistration_sha256")==sha256((ROOT/"preregistration.json").read_bytes()).hexdigest(),
 "source_hash":r.get("source_manifest_sha256")==sha256((ROOT/"source_manifest.json").read_bytes()).hexdigest(),
 "freeze_hash":r.get("freeze_sha256")==sha256((ROOT/"FREEZE.json").read_bytes()).hexdigest(),
 "authority_none":r.get("policy_authority")=="NONE",
 "runtime_none":r.get("runtime_permission")=="NONE",
}
if r.get("verdict") in {"SELECTIVE_LOCALIZATION_ADVANTAGE","CAPABILITY_PARITY","SAFETY_FAILURE"}:
    t0=json.loads((ROOT/"t0_model.json").read_text())
    ints=json.loads((ROOT/"interventions.json").read_text())
    traces=[json.loads(x) for x in (ROOT/"external_traces.jsonl").read_text().splitlines() if x.strip()]
    expected=adjudicate(t0,traces,ints["pool"],P)
    checks["verdict_recomputed"]=expected["verdict"]==r["verdict"]
    for label,path in [
      ("source_binding",ROOT/"t0_source_binding.json"),("t0_model",ROOT/"t0_model.json"),
      ("t0_receipts",ROOT/"t0_receipts.jsonl"),("interventions",ROOT/"interventions.json"),
      ("external_traces",ROOT/"external_traces.jsonl")
    ]:
        checks[label+"_hash"]=r.get(label+"_sha256")==sha256(path.read_bytes()).hexdigest()
elif r.get("verdict")=="DATA_INSUFFICIENT":
    checks["has_detail_or_data_gate"]=bool(r.get("detail") or r.get("data_sufficiency"))
out={"schema":"openline.ace.psd001.result-verification.v1","verified":all(checks.values()),"checks":checks,"verdict":r.get("verdict")}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
