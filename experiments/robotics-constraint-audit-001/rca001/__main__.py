import argparse,json
from .core import run,grade
p=argparse.ArgumentParser(); s=p.add_subparsers(dest="cmd",required=True); c=s.add_parser("conformance"); c.add_argument("--out",required=True); c.add_argument("--trials",type=int,default=64); g=s.add_parser("grade"); g.add_argument("--results",required=True); a=p.parse_args()
if a.cmd=="conformance": print(json.dumps(grade(run(a.out,a.trials)),indent=2,sort_keys=True))
else: print(json.dumps(grade(a.results),indent=2,sort_keys=True))
