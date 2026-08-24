from pathlib import Path
from hashlib import sha256
import json

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
manifest = json.loads((ROOT / "RELEASE_MANIFEST.json").read_text())
expected = {item["path"]: item for item in manifest["files"]}

scope = [path for path in ROOT.rglob("*") if path.is_file()]
scope.extend(
    [
        REPO / ".github/workflows/ace-standing-loss-lead-time-001.yml",
        REPO / "SLD001_HANDOFF.json",
    ]
)

actual = {}
for path in sorted(set(scope)):
    if not path.is_file():
        continue
    rel = path.relative_to(REPO).as_posix()
    if rel == "experiments/standing-loss-lead-time-001/RELEASE_MANIFEST.json":
        continue
    if "__pycache__" in path.parts or path.suffix == ".pyc":
        continue
    data = path.read_bytes()
    actual[rel] = {"sha256": sha256(data).hexdigest(), "size": len(data)}

checks = {
    "closure": set(actual) == set(expected),
    "hashes": all(
        rel in actual and actual[rel]["sha256"] == item["sha256"]
        for rel, item in expected.items()
    ),
    "sizes": all(
        rel in actual and actual[rel]["size"] == item["size"]
        for rel, item in expected.items()
    ),
    "policy_authority_none": manifest.get("policy_authority") == "NONE",
    "runtime_permission_none": manifest.get("runtime_permission") == "NONE",
}
out = {
    "schema": "openline.ace.sld001.release-verification.v1",
    "verified": all(checks.values()),
    "checks": checks,
    "file_count": len(actual),
}
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
