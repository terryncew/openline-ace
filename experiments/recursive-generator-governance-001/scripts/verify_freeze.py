from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
FREEZE_PATH = ROOT / "FREEZE.json"

freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
expected = {item["path"]: item["sha256"] for item in freeze["files"]}

scoped = set()
for path in sorted(ROOT.rglob("*")):
    if not path.is_file():
        continue
    if path == FREEZE_PATH or "__pycache__" in path.parts or path.suffix == ".pyc":
        continue
    rel = path.relative_to(REPO_ROOT).as_posix()
    scoped.add(rel)

workflow_rel = ".github/workflows/recursive-generator-governance-001.yml"
workflow_path = REPO_ROOT / workflow_rel
if workflow_path.is_file():
    scoped.add(workflow_rel)

missing = sorted(path for path in expected if not (REPO_ROOT / path).is_file())
extra = sorted(scoped - set(expected))
unscoped = sorted(set(expected) - scoped)
changed = []
for rel, digest in sorted(expected.items()):
    path = REPO_ROOT / rel
    if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        changed.append(rel)

if missing or extra or unscoped or changed:
    raise SystemExit(
        "freeze mismatch "
        f"missing={missing} extra={extra} unscoped={unscoped} changed={changed}"
    )

print(f"PASS freeze files={len(expected)} scope=RGG-001+workflow")
