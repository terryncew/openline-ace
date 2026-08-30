from pathlib import Path
import hashlib, json
ROOT=Path(__file__).resolve().parents[1]
freeze=json.loads((ROOT/'FREEZE.json').read_text())
expected={x['path']:x['sha256'] for x in freeze['files']}
repo_root=ROOT.parents[1]
actual={}
for path in sorted(repo_root.rglob('*')):
    if not path.is_file(): continue
    rel=path.relative_to(repo_root).as_posix()
    if rel.endswith('/FREEZE.json') or '__pycache__' in rel: continue
    actual[rel]=hashlib.sha256(path.read_bytes()).hexdigest()
missing=sorted(set(expected)-set(actual)); extra=sorted(set(actual)-set(expected)); changed=sorted(p for p in expected.keys() & actual.keys() if expected[p]!=actual[p])
if missing or extra or changed:
    raise SystemExit(f'freeze mismatch missing={missing} extra={extra} changed={changed}')
print(f'PASS freeze files={len(expected)}')
