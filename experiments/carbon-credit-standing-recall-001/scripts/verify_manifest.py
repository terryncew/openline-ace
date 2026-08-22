from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    manifest_path = ROOT / "RELEASE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = manifest["files"]
    actual_paths = sorted(
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.name != "RELEASE_MANIFEST.json"
        and "__pycache__" not in path.parts
    )
    if sorted(expected) != actual_paths:
        missing = sorted(set(expected) - set(actual_paths))
        extra = sorted(set(actual_paths) - set(expected))
        raise SystemExit(f"manifest closure mismatch missing={missing} extra={extra}")

    for rel, digest in expected.items():
        actual = sha256(ROOT / rel)
        if actual != digest:
            raise SystemExit(f"manifest hash mismatch {rel}")

    print(f"ccr001_manifest_verified files={len(actual_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
