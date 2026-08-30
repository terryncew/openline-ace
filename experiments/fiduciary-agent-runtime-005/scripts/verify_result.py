from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from far005.experiment import adjudicate
ap=argparse.ArgumentParser(); ap.add_argument('--result-dir',required=True); a=ap.parse_args(); r=json.loads((Path(a.result_dir)/'result.json').read_text()); p=json.loads((ROOT/'PREREGISTRATION.json').read_text()); expected=adjudicate(p,r['metrics'],r['integrity']); assert r['verdict']==expected,(r['verdict'],expected); assert r['scientific_standing']=='PROSPECTIVE_PRIMARY'; print('PASS result verdict',expected)
