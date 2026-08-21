#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    manifest = json.loads((ROOT / "RELEASE_MANIFEST.json").read_text())
    expected = manifest["files"]
    actual_paths = sorted(
        str(p.relative_to(ROOT)) for p in ROOT.rglob("*")
        if p.is_file() and p.name != "RELEASE_MANIFEST.json" and "__pycache__" not in p.parts
    )
    if actual_paths != sorted(expected):
        raise SystemExit(f"release closure mismatch expected={len(expected)} actual={len(actual_paths)}")
    for name, meta in expected.items():
        p = ROOT / name
        if p.stat().st_size != meta["size"] or sha(p) != meta["sha256"]:
            raise SystemExit(f"release file mismatch: {name}")
    print(json.dumps({"release_closure": "verified", "files": len(actual_paths)}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
