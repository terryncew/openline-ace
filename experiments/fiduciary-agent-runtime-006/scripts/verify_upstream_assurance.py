from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
pins = json.loads((ROOT / "UPSTREAM_ASSURANCE_PINS.json").read_text())
bad = []
for relative, expected in pins["files"].items():
    path = REPO / relative
    observed = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    if observed != expected:
        bad.append((relative, observed, expected))
assert not bad, f"upstream assurance pin mismatch: {bad}"
print(f"PASS upstream assurance pins={len(pins['files'])}")
