from __future__ import annotations
import hashlib
import json
from pathlib import Path
import py_compile
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

# Unit tests
suite = unittest.defaultTestLoader.discover(str(HERE / "tests"))
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)

# Rebuild deterministic result
subprocess.run([sys.executable, str(HERE / "scripts" / "run.py")], check=True)

# Result contract
out = json.loads((HERE / "evidence" / "result.json").read_text())
assert out["status"] == "EXTERNAL_REGULATORY_RECALL_PASS"
assert out["policy_authority"] == "NONE"
assert out["runtime_permission"] == "NONE"
assert out["patient_specific_advice"] == "NONE"

# Source fact shape
src = json.loads((HERE / "evidence" / "source_facts.json").read_text())
assert src["case_id"] == "dmhc-cigna-23-262"
assert len(src["sources"]) == 3
assert len(src["facts"]) >= 6

# Grammar/import check for local Python files
for p in sorted(HERE.rglob("*.py")):
    py_compile.compile(str(p), doraise=True)

# Manifest closure
manifest_path = HERE / "RELEASE_MANIFEST.json"
manifest = json.loads(manifest_path.read_text())
expected = manifest["files"]
actual_paths = sorted(
    p.relative_to(HERE).as_posix()
    for p in HERE.rglob("*")
    if p.is_file()
    and "__pycache__" not in p.parts
    and p.name != "RELEASE_MANIFEST.json"
)
if sorted(expected) != actual_paths:
    raise SystemExit(f"manifest closure mismatch\nexpected={sorted(expected)}\nactual={actual_paths}")
for rel, expected_hash in expected.items():
    actual_hash = sha256(HERE / rel)
    if actual_hash != expected_hash:
        raise SystemExit(f"manifest hash mismatch {rel}: {actual_hash} != {expected_hash}")

print("HDR-001 release check passed")
print("status=EXTERNAL_REGULATORY_RECALL_PASS")
print("policy_authority=NONE")
print("runtime_permission=NONE")
print("patient_specific_advice=NONE")
