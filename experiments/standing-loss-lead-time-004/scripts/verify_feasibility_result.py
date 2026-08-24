from pathlib import Path
from hashlib import sha256
import json
ROOT=Path(__file__).resolve().parents[1]
p=json.loads((ROOT/"preregistration.json").read_text())
r=json.loads((ROOT/"feasibility_result.json").read_text())
checks={
 "allowed_verdict":r.get("verdict") in set(p["f0"]["allowed_verdicts"]),
 "h1_unadjudicated":r.get("scientific_h1_adjudicated") is False,
 "candidate_set_exact":[x["candidate_id"] for x in r["candidate_results"]]==p["f0"]["candidate_ids"],
 "fail_closed":(r["verdict"]=="FEASIBILITY_NOT_ESTABLISHED") == (not r["checks"]["all_three_complete"]),
 "authority_none":r.get("policy_authority")=="NONE",
 "runtime_none":r.get("runtime_permission")=="NONE"
}
out={"schema":"openline.ace.sld004.f0-verification.v1","verified":all(checks.values()),"checks":checks,"verdict":r.get("verdict")}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
