from pathlib import Path
from hashlib import sha256
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sld002.core import evaluate

stored = json.loads((ROOT / "external_result.json").read_text())
prereg = json.loads((ROOT / "preregistration.json").read_text())
cases = [
    json.loads(line)
    for line in (ROOT / "external_cases.jsonl").read_text().splitlines()
    if line.strip()
]

source_ok = stored.get("verdict") != "SOURCE_ACCESS_FAILED"
recomputed = evaluate(cases, prereg, source_access_ok=source_ok)

checks = {
    "allowed_verdict": stored.get("verdict") in set(prereg["allowed_verdicts"]),
    "recomputed_core": all(
        stored.get(key) == recomputed.get(key) for key in recomputed
    ),
    "preregistration_hash": (
        stored.get("preregistration_sha256")
        == sha256((ROOT / "preregistration.json").read_bytes()).hexdigest()
    ),
    "source_manifest_hash": (
        stored.get("source_manifest_sha256")
        == sha256((ROOT / "source_manifest.json").read_bytes()).hexdigest()
    ),
    "freeze_hash": (
        stored.get("freeze_sha256")
        == sha256((ROOT / "FREEZE.json").read_bytes()).hexdigest()
    ),
    "external_raw_hash": (
        stored.get("external_raw_sha256")
        == sha256((ROOT / "external_raw.json").read_bytes()).hexdigest()
    ),
    "external_cases_hash": (
        stored.get("external_cases_sha256")
        == sha256((ROOT / "external_cases.jsonl").read_bytes()).hexdigest()
    ),
    "authority_none": stored.get("policy_authority") == "NONE",
    "runtime_none": stored.get("runtime_permission") == "NONE",
}
out = {
    "schema": "openline.ace.sld002.result-verification.v1",
    "verified": all(checks.values()),
    "checks": checks,
    "verdict": stored.get("verdict"),
}
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
