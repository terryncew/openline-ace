from __future__ import annotations
import json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from far003.controls import run_controls
r=run_controls(ROOT); print(json.dumps(r,indent=2,sort_keys=True)); raise SystemExit(0 if r['passed'] else 1)
