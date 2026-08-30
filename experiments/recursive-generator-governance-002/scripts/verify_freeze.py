from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
FREEZE = ROOT / "FREEZE.json"
freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
expected = {item["path"]: item["sha256"] for item in freeze["files"]}

scoped = set()
for path in ROOT.rglob("*"):
    if not path.is_file() or path == FREEZE or "__pycache__" in path.parts or path.suffix == ".pyc":
        continue
    scoped.add(path.relative_to(REPO_ROOT).as_posix())
workflow = REPO_ROOT / ".github/workflows/recursive-generator-governance-002.yml"
if workflow.is_file():
    scoped.add(workflow.relative_to(REPO_ROOT).as_posix())

missing = sorted(k for k in expected if not (REPO_ROOT / k).is_file())
extra = sorted(scoped - set(expected))
changed = []
for rel, digest in expected.items():
    path = REPO_ROOT / rel
    if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        changed.append(rel)
if missing or extra or changed:
    raise SystemExit(f"freeze mismatch missing={missing} extra={extra} changed={sorted(changed)}")
print(f"PASS freeze files={len(expected)} scope=RGG-002+workflow")
