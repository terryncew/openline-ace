from __future__ import annotations
import hashlib, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]; repo=ROOT.parents[1]
f=json.loads((ROOT/'FREEZE.json').read_text())
for rel, expected in f['files'].items():
    p=repo/rel
    assert p.exists(), f'missing frozen file: {rel}'
    got=hashlib.sha256(p.read_bytes()).hexdigest()
    assert got==expected, f'freeze mismatch {rel}: {got} != {expected}'
print(f"PASS freeze_files={len(f['files'])}")
