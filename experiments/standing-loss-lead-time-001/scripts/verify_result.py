from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sld001.core import evaluate

cases = json.loads((ROOT / "frozen_cases.json").read_text())
prereg = json.loads((ROOT / "preregistration.json").read_text())
freeze = json.loads((ROOT / "FREEZE.json").read_text())
actual = json.loads((ROOT / "results" / "result.json").read_text())
expected = evaluate(cases, prereg)
expected["preregistration_sha256"] = freeze["preregistration_sha256"]
expected["frozen_cases_sha256"] = freeze["frozen_cases_sha256"]
checks = {
    "exact_recompute": actual == expected,
    "allowed_verdict": actual.get("verdict") in prereg["allowed_verdicts"],
    "standing_loss_is_resolved_time": prereg["standing_loss_definition"].startswith("t_resolved"),
    "policy_authority_none": actual.get("policy_authority") == "NONE",
    "runtime_permission_none": actual.get("runtime_permission") == "NONE",
}
out = {"schema": "openline.ace.sld001.result-verification.v1", "verified": all(checks.values()), "checks": checks, "verdict": actual.get("verdict")}
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
