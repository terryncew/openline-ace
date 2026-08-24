from pathlib import Path
from hashlib import sha256
import json
ROOT=Path(__file__).resolve().parents[1]
f=json.loads((ROOT/"FREEZE.json").read_text())
checks={
 "prereg":f["preregistration_sha256"]==sha256((ROOT/"preregistration.json").read_bytes()).hexdigest(),
 "source":f["source_manifest_sha256"]==sha256((ROOT/"source_manifest.json").read_bytes()).hexdigest(),
 "core":f["core_sha256"]==sha256((ROOT/"psd001/core.py").read_bytes()).hexdigest(),
 "oracle":f["oracle_sha256"]==sha256((ROOT/"psd001/oracle.py").read_bytes()).hexdigest(),
 "runner":f["external_runner_sha256"]==sha256((ROOT/"scripts/run_external.py").read_bytes()).hexdigest(),
 "target_substitution_off":f["target_substitution_allowed"] is False,
 "commit_change_off":f["upstream_commit_change_allowed"] is False,
 "policy_change_off":f["policy_change_after_run_allowed"] is False,
 "authority_none":f["policy_authority"]=="NONE",
 "runtime_none":f["runtime_permission"]=="NONE",
}
out={"schema":"openline.ace.psd001.freeze-verification.v1","verified":all(checks.values()),"checks":checks}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
