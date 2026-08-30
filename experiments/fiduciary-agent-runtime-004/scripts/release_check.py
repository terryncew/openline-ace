from __future__ import annotations
import json, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
pr=json.loads((ROOT/'PREREGISTRATION.json').read_text())
assert pr['scientific_standing']=='PROTOCOL_FROZEN_PRE_PRIMARY_OUTCOME'
assert pr['base_commit']=='1a9a6cab081982c0bebf385258f35b098b14f778'
for script in ('verify_freeze.py','verify_upstream_runtime.py'):
    subprocess.run([sys.executable,str(ROOT/'scripts'/script)],cwd=ROOT,check=True)
r=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-p','test_*.py'],cwd=ROOT)
if r.returncode: raise SystemExit(r.returncode)
# Reuse FAR-003 power calibration without running FAR-004 primary.
far003=ROOT.parent/'fiduciary-agent-runtime-003'
raise SystemExit(subprocess.run([sys.executable,str(far003/'scripts/run_controls.py')],cwd=far003).returncode)
