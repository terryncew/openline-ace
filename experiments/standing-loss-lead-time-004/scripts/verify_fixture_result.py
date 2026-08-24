from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/"fixture_result.json").read_text())
m=r["metrics"]
checks={
 "synthetic_excluded": r.get("scientific_evidence") is False,
 "all_valid": r.get("all_cases_admissible") is True,
 "olp_perfect_recall": m["openline_evidence_dag"]["decision_recall"] == 1.0,
 "olp_perfect_precision": m["openline_evidence_dag"]["decision_precision"] == 1.0,
 "strong_artifact_not_strawman": m["artifact_component_join"]["decision_recall"] == 1.0,
 "artifact_join_overreopens_semantic_controls": m["artifact_component_join"]["false_reopen_rate"] > m["openline_evidence_dag"]["false_reopen_rate"],
 "repo_join_no_better_than_artifact": m["repo_scope_flat_join"]["false_reopen_rate"] >= m["artifact_component_join"]["false_reopen_rate"],
 "headline_has_no_pretruth_recall": m["headline_only"]["decision_recall"] == 0.0,
 "authority_none":r.get("policy_authority")=="NONE",
 "runtime_none":r.get("runtime_permission")=="NONE"
}
out={"schema":"openline.ace.sld004.fixture-verification.v1","verified":all(checks.values()),"checks":checks}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
