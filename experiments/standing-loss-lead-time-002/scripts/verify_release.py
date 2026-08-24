from pathlib import Path
from hashlib import sha256
import json

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
manifest = json.loads((ROOT / "RELEASE_MANIFEST.json").read_text())
expected = {item["path"]: item for item in manifest["files"]}

actual = {}
for rel, item in expected.items():
    path = REPO / rel
    if path.is_file():
        data = path.read_bytes()
        actual[rel] = {
            "sha256": sha256(data).hexdigest(),
            "size": len(data),
        }

experiment_files = set()
for path in ROOT.rglob("*"):
    if (
        not path.is_file()
        or "__pycache__" in path.parts
        or path.suffix == ".pyc"
        or path.name == "RELEASE_MANIFEST.json"
    ):
        continue
    if path.name in {
        "external_raw.json",
        "external_cases.jsonl",
        "external_result.json",
    }:
        continue
    experiment_files.add(path.relative_to(REPO).as_posix())

expected_experiment = {
    rel
    for rel in expected
    if rel.startswith("experiments/standing-loss-lead-time-002/")
}

checks = {
    "all_declared_present": set(actual) == set(expected),
    "experiment_closure": experiment_files == expected_experiment,
    "hashes": all(
        actual.get(rel, {}).get("sha256") == item["sha256"]
        for rel, item in expected.items()
    ),
    "sizes": all(
        actual.get(rel, {}).get("size") == item["size"]
        for rel, item in expected.items()
    ),
    "policy_authority_none": manifest.get("policy_authority") == "NONE",
    "runtime_permission_none": manifest.get("runtime_permission") == "NONE",
}
out = {
    "schema": "openline.ace.sld002.release-verification.v1",
    "verified": all(checks.values()),
    "checks": checks,
    "file_count": len(actual),
}
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
