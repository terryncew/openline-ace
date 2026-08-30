from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from far005.experiment import run_primary
ap=argparse.ArgumentParser(); ap.add_argument('--output',required=True); a=ap.parse_args(); p=json.loads((ROOT/'PREREGISTRATION.json').read_text()); r=run_primary(Path(a.output),p,ROOT); print(r['verdict'])
