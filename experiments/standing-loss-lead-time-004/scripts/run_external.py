from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sld004.core import adjudicate
p=json.loads((ROOT/"preregistration.json").read_text())
case_dir=ROOT/"historical_cases"
if not case_dir.is_dir():
    out={"schema":"openline.ace.sld004.f1-result.v1","experiment_id":"SLD-004","verdict":"DATA_INSUFFICIENT","reason":"historical_cases_directory_absent","policy_authority":"NONE","runtime_permission":"NONE"}
else:
    cases=[json.loads(x.read_text()) for x in sorted(case_dir.glob("*.json"))]
    out={"schema":"openline.ace.sld004.f1-result.v1","experiment_id":"SLD-004",**adjudicate(cases,p)}
(ROOT/"external_result.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
print(json.dumps(out,indent=2,sort_keys=True))
