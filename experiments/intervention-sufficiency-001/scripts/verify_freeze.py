from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    freeze = json.loads((ROOT / "FREEZE.json").read_text(encoding="utf-8"))
    errors = []
    for item in freeze["files"]:
        path = ROOT / item["path"]
        if not path.is_file():
            errors.append(f"missing:{item['path']}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            errors.append(f"hash:{item['path']}")
    print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
