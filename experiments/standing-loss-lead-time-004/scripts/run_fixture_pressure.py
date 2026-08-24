from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sld004.core import validate_case, predictions, confusion
cases=[json.loads(p.read_text()) for p in sorted((ROOT/"fixtures").glob("*.json"))]
valid=[validate_case(c) for c in cases]
strategies=("openline_evidence_dag","artifact_component_join","repo_scope_flat_join","any_change","ttl_freshness","headline_only")
result={
 "schema":"openline.ace.sld004.fixture-pressure.v1",
 "scientific_evidence":False,
 "all_cases_admissible":all(v["admissible"] for v in valid),
 "case_validations":valid,
 "metrics":{s:confusion(cases,s) for s in strategies},
 "policy_authority":"NONE","runtime_permission":"NONE"
}
(ROOT/"fixture_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2,sort_keys=True))
raise SystemExit(0 if result["all_cases_admissible"] else 2)
