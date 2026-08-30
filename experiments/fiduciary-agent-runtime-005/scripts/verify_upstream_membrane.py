from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]; REPO=ROOT.parents[1]; pins=json.loads((ROOT/'UPSTREAM_MEMBRANE_PINS.json').read_text()); bad=[]
for rel,exp in pins['files'].items():
 p=REPO/rel; got=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
 if got!=exp: bad.append((rel,got,exp))
assert not bad, f'upstream membrane pin mismatch: {bad}'
print('PASS upstream membrane pins')
