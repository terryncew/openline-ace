from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/"fixture_result.json").read_text())
m=r["complete_metrics"]
checks={
 "not_scientific":r["scientific_evidence"] is False,
 "thirty_decisions":r["t0_decisions"]==30,
 "olp_full_recall":m["openline_evidence_graph"]["decision_recall"]==1.0,
 "olp_precision_gt_artifact":m["openline_evidence_graph"]["decision_precision"]>m["artifact_component_join"]["decision_precision"],
 "equivalent_index_matches":r["equivalence_mismatches"]==0,
 "missing_is_undetermined":r["missing_prediction"]=="UNDETERMINED",
 "authority_none":r["policy_authority"]=="NONE",
 "runtime_none":r["runtime_permission"]=="NONE",
}
out={"schema":"openline.ace.psd001.fixture-verification.v1","verified":all(checks.values()),"checks":checks}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
