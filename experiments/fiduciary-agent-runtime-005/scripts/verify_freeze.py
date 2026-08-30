from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]; REPO=ROOT.parents[1]; f=json.loads((ROOT/'FREEZE.json').read_text()); bad=[]
for rel,exp in f['files'].items():
 p=REPO/rel; got=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
 if got!=exp: bad.append((rel,got,exp))
assert not bad, f'freeze mismatch: {bad}'
print(f"PASS freeze files={len(f['files'])}")
