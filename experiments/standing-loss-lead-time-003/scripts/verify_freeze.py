from pathlib import Path
from hashlib import sha256
import json

ROOT = Path(__file__).resolve().parents[1]
f = json.loads((ROOT / "FREEZE.json").read_text())
checks = {
    "preregistration": f["preregistration_sha256"] == sha256((ROOT / "preregistration.json").read_bytes()).hexdigest(),
    "source_manifest": f["source_manifest_sha256"] == sha256((ROOT / "source_manifest.json").read_bytes()).hexdigest(),
    "core": f["core_sha256"] == sha256((ROOT / "sld003/core.py").read_bytes()).hexdigest(),
    "runner": f["external_runner_sha256"] == sha256((ROOT / "scripts/run_external.py").read_bytes()).hexdigest(),
    "pre_external": f.get("freeze_stage") == "before_external_fetch",
    "anti_rescue": f.get("anti_rescue") is True,
    "authority_none": f.get("policy_authority") == "NONE",
    "runtime_none": f.get("runtime_permission") == "NONE",
}
out = {"schema":"openline.ace.sld003.freeze-verification.v1","verified":all(checks.values()),"checks":checks}
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
