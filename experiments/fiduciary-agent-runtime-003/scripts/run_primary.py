from __future__ import annotations
import argparse, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from far003.experiment import run_primary
p=argparse.ArgumentParser(); p.add_argument('--output',required=True); a=p.parse_args(); prereg=json.loads((ROOT/'PREREGISTRATION.json').read_text()); r=run_primary(pathlib.Path(a.output),prereg,ROOT); print(json.dumps(r['metrics'],indent=2,sort_keys=True)); print(r['verdict'])
