from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
manifest = json.loads((ROOT / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()

errors = []
for item in manifest["files"]:
    path = REPO_ROOT / item["path"]
    if not path.is_file():
        errors.append(f"missing:{item['path']}")
        continue
    actual = git_blob_sha1(path.read_bytes())
    if actual != item["git_blob_sha1"]:
        errors.append(f"changed:{item['path']}:{actual}")

if manifest.get("rgg001_external_evaluator_reuse_permitted") is not False:
    errors.append("RGG-001 external evaluator reuse must remain forbidden")

if errors:
    raise SystemExit("source pin failure " + "; ".join(errors))
print(f"PASS source pins={len(manifest['files'])} rgg001_external_reuse=False")
