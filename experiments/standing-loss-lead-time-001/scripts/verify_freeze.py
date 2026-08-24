from pathlib import Path
from hashlib import sha256
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
freeze = json.loads((ROOT / "FREEZE.json").read_text())
checks = {}
for name in ["preregistration", "frozen_cases"]:
    path = ROOT / (name + ".json")
    checks[name] = sha256(path.read_bytes()).hexdigest() == freeze[name + "_sha256"]
checks["policy_authority_none"] = freeze.get("policy_authority") == "NONE"
checks["runtime_permission_none"] = freeze.get("runtime_permission") == "NONE"
out = {"schema": "openline.ace.sld001.freeze-verification.v1", "verified": all(checks.values()), "checks": checks}
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
