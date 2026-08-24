from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from psd001.core import parse_metadata,build_t0_model,run_trial,confusion,equivalence_mismatches
targets=json.loads((ROOT/"source_manifest.json").read_text())["target_crates"]
meta=json.loads((ROOT/"fixtures/metadata.json").read_text())
proj=parse_metadata(meta,targets)
t0=build_t0_model(proj,targets,True,{t:"f"*64 for t in targets})
shared=next(c for c in proj["union"]["uv-auth"] if "serde@1.0.0" in c)
single=next(c for c in proj["union"]["uv-auth"] if "ring@1.0.0" in c)
absent=proj["absent_components"][0]
trials=[
 {"trial_id":"shared","arm":"complete_graph","stratum":"shared","component_id":shared,"graph_damage":None},
 {"trial_id":"single","arm":"complete_graph","stratum":"single","component_id":single,"graph_damage":None},
 {"trial_id":"absent","arm":"complete_graph","stratum":"absent","component_id":absent,"graph_damage":None},
 {"trial_id":"missing","arm":"known_missing_edge","stratum":"single","component_id":single,
  "graph_damage":{"target":"uv-auth","kind":"runtime","known_incomplete":True}},
]
traces=[run_trial(t0,t) for t in trials]
result={
 "schema":"openline.ace.psd001.fixture-pressure.v1",
 "scientific_evidence":False,
 "t0_decisions":len(t0["decisions"]),
 "complete_metrics":{
   s:confusion(traces,s) for s in ("openline_evidence_graph","artifact_component_join","repo_scope_join","decision_closure_index","headline_only")
 },
 "equivalence_mismatches":equivalence_mismatches(traces),
 "missing_prediction":traces[-1]["predictions"]["openline_evidence_graph"]["decision:uv-auth:runtime_security_acceptance"],
 "policy_authority":"NONE","runtime_permission":"NONE"
}
(ROOT/"fixture_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2,sort_keys=True))
