from __future__ import annotations
import hashlib, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
pins=json.loads((ROOT/'UPSTREAM_RUNTIME_PINS.json').read_text())
for rel,expected in pins['files'].items():
    p=REPO/rel
    assert p.exists(), f'missing upstream runtime file: {rel}'
    got=hashlib.sha256(p.read_bytes()).hexdigest()
    assert got==expected, f'upstream runtime mismatch {rel}: {got} != {expected}'
print(f"PASS upstream_runtime_pins={len(pins['files'])}")
