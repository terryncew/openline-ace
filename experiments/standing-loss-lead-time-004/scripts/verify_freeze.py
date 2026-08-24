from pathlib import Path
from hashlib import sha256
import json
ROOT=Path(__file__).resolve().parents[1]
f=json.loads((ROOT/"FREEZE.json").read_text())
checks={
 "preregistration":f["preregistration_sha256"]==sha256((ROOT/"preregistration.json").read_bytes()).hexdigest(),
 "candidate_registry":f["feasibility_candidates_sha256"]==sha256((ROOT/"feasibility_candidates.json").read_bytes()).hexdigest(),
 "source_requirements":f["source_requirements_sha256"]==sha256((ROOT/"source_requirements.json").read_bytes()).hexdigest(),
 "core":f["core_sha256"]==sha256((ROOT/"sld004/core.py").read_bytes()).hexdigest(),
 "candidate_substitution_disabled":f.get("candidate_substitution_allowed") is False,
 "future_backfill_disabled":f.get("future_outcome_edge_backfill_allowed") is False,
 "authority_none":f.get("policy_authority")=="NONE",
 "runtime_none":f.get("runtime_permission")=="NONE"
}
for cid,digest in f["candidate_packets"].items():
    checks[f"packet:{cid}"]=digest==sha256((ROOT/"feasibility"/f"{cid}.json").read_bytes()).hexdigest()
out={"schema":"openline.ace.sld004.freeze-verification.v1","verified":all(checks.values()),"checks":checks}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
