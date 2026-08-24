from pathlib import Path
from hashlib import sha256
import json

ROOT = Path(__file__).resolve().parents[1]
freeze = json.loads((ROOT / "FREEZE.json").read_text())

checks = {
    "preregistration_hash": (
        freeze["preregistration_sha256"]
        == sha256((ROOT / "preregistration.json").read_bytes()).hexdigest()
    ),
    "source_manifest_hash": (
        freeze["source_manifest_sha256"]
        == sha256((ROOT / "source_manifest.json").read_bytes()).hexdigest()
    ),
    "core_hash": (
        freeze["core_sha256"]
        == sha256((ROOT / "sld002/core.py").read_bytes()).hexdigest()
    ),
    "external_runner_hash": (
        freeze["external_runner_sha256"]
        == sha256((ROOT / "scripts/run_external.py").read_bytes()).hexdigest()
    ),
    "freeze_before_external_fetch": (
        freeze.get("freeze_stage") == "before_external_fetch"
    ),
    "anti_rescue": freeze.get("anti_rescue") is True,
    "authority_none": freeze.get("policy_authority") == "NONE",
    "runtime_none": freeze.get("runtime_permission") == "NONE",
}
out = {
    "schema": "openline.ace.sld002.freeze-verification.v1",
    "verified": all(checks.values()),
    "checks": checks,
}
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
