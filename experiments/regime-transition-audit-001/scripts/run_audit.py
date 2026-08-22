from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from rta001.core import evaluate
p=json.loads((ROOT/"preregistration.json").read_text()); rows=[json.loads(x) for x in (ROOT/"fixture.jsonl").read_text().splitlines() if x.strip()]
r=evaluate(rows,p); r["fixture_sha256"]=hashlib.sha256((ROOT/"fixture.jsonl").read_bytes()).hexdigest(); r["preregistration_sha256"]=hashlib.sha256((ROOT/"preregistration.json").read_bytes()).hexdigest(); (ROOT/"result.json").write_text(json.dumps(r,indent=2,sort_keys=True)+"\n"); print(json.dumps(r,indent=2,sort_keys=True))
