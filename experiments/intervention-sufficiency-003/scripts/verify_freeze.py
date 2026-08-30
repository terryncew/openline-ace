from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
FREEZE_PATH = ROOT / "FREEZE.json"

freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
expected = {item["path"]: item["sha256"] for item in freeze["files"]}

# The freeze manifest governs IS-003 plus its single workflow file. It must not
# treat unrelated, pre-existing repository content (or .git metadata) as part
# of this experiment's frozen surface.
scoped_paths = set()
for path in sorted(ROOT.rglob("*")):
    if not path.is_file():
        continue
    rel = path.relative_to(REPO_ROOT).as_posix()
    if path == FREEZE_PATH or "__pycache__" in path.parts or path.suffix == ".pyc":
        continue
    scoped_paths.add(rel)

workflow_rel = ".github/workflows/intervention-sufficiency-003.yml"
workflow_path = REPO_ROOT / workflow_rel
if workflow_path.is_file():
    scoped_paths.add(workflow_rel)

missing = sorted(path for path in expected if not (REPO_ROOT / path).is_file())
extra = sorted(scoped_paths - set(expected))
unscoped = sorted(set(expected) - scoped_paths)
changed = []
for rel, digest in sorted(expected.items()):
    path = REPO_ROOT / rel
    if not path.is_file():
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != digest:
        changed.append(rel)

if missing or extra or unscoped or changed:
    raise SystemExit(
        "freeze mismatch "
        f"missing={missing} extra={extra} unscoped={unscoped} changed={changed}"
    )

print(f"PASS freeze files={len(expected)} scope=IS-003+workflow")
