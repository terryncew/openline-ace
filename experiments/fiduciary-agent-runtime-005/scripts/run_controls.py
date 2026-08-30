from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from far005.controls import run_controls
r=run_controls(ROOT); print(json.dumps(r,indent=2,sort_keys=True)); raise SystemExit(0 if r['passed'] else 1)
