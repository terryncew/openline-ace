from pathlib import Path
from hashlib import sha256
import json

ROOT = Path(__file__).resolve().parents[1]
f = json.loads((ROOT / "FREEZE.json").read_text())
checks = {
    "preregistration": f["preregistration_sha256"] == sha256((ROOT/"PREREGISTRATION.json").read_bytes()).hexdigest(),
    "source_manifest": f["source_manifest_sha256"] == sha256((ROOT/"SOURCE_MANIFEST.json").read_bytes()).hexdigest(),
    "thresholds": f["thresholds_sha256"] == sha256((ROOT/"GINKGO_THRESHOLDS.json").read_bytes()).hexdigest(),
    "selector": f["selector_sha256"] == sha256((ROOT/"external_selector.py").read_bytes()).hexdigest(),
    "runner": f["external_runner_sha256"] == sha256((ROOT/"scripts/run_external.py").read_bytes()).hexdigest(),
    "jain_identity_projection": f["jain_identity_projection_sha256"] == sha256((ROOT/"JAIN_2017_CANONICAL_COHORT.bound.json").read_bytes()).hexdigest(),
    "packaging_repair_receipt": f["packaging_repair_receipt_sha256"] == sha256((ROOT/"PACKAGING_REPAIR_RECEIPT.json").read_bytes()).hexdigest(),
    "pre_external": f.get("freeze_stage") == "before_external_scoring",
    "anti_rescue": f.get("anti_rescue") is True,
    "authority_none": f.get("policy_authority") == "NONE",
    "runtime_none": f.get("runtime_permission") == "NONE",
}
out = {"schema":"openline.trial-selector.ginkgo.freeze-verification.v1","verified":all(checks.values()),"checks":checks}
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
