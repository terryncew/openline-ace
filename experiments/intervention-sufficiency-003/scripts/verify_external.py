import argparse, hashlib, json
from pathlib import Path
ap=argparse.ArgumentParser(); ap.add_argument('--result-dir',type=Path,required=True); args=ap.parse_args()
rp=args.result_dir/'result.json'; r=json.loads(rp.read_text())
if r.get('experiment_id')!='IS-003': raise SystemExit('wrong experiment id')
if r.get('pilot_outcomes_used') is not False: raise SystemExit('pilot outcome contamination')
if r.get('policy_authority')!='NONE' or r.get('execution_authority')!='NONE': raise SystemExit('authority contamination')
expected=(args.result_dir/'result.sha256').read_text().split()[0]; actual=hashlib.sha256(rp.read_bytes()).hexdigest()
if expected!=actual: raise SystemExit('result hash mismatch')
print(f"PASS receipt_integrity verdict={r['verdict']} sha256={actual}")
