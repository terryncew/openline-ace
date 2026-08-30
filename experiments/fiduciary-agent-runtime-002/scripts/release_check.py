from __future__ import annotations
import json, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
pr=json.loads((ROOT/'PREREGISTRATION.json').read_text()); assert pr['scientific_standing']=='PROTOCOL_FROZEN_PRE_PRIMARY_OUTCOME'; assert pr['base_commit']=='b82e3bdd65c3ef397f0cae7c1204124293971764'
subprocess.run([sys.executable,str(ROOT/'scripts/verify_freeze.py')],cwd=ROOT,check=True)
r=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-p','test_*.py'],cwd=ROOT); raise SystemExit(r.returncode)
