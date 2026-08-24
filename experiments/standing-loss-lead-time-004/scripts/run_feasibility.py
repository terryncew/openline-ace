from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
p=json.loads((ROOT/"preregistration.json").read_text())
registry=json.loads((ROOT/"feasibility_candidates.json").read_text())
expected=p["f0"]["candidate_ids"]
found=[c["candidate_id"] for c in registry["candidates"]]
rows=[]
for c in registry["candidates"]:
    packet=json.loads((ROOT/c["case_packet"]).read_text())
    missing=list(packet.get("missing_required_evidence") or [])
    rows.append({
      "candidate_id":c["candidate_id"],
      "packet_status":packet.get("current_packet_status"),
      "complete":packet.get("current_packet_status")=="COMPLETE" and not missing,
      "missing_required_evidence":missing
    })
checks={
 "candidate_set_exact":found==expected,
 "candidate_substitution_disabled":registry.get("candidate_substitution_allowed") is False,
 "all_three_complete":all(r["complete"] for r in rows)
}
verdict="FEASIBILITY_ESTABLISHED" if all(checks.values()) else "FEASIBILITY_NOT_ESTABLISHED"
out={
 "schema":"openline.ace.sld004.f0-result.v1",
 "experiment_id":"SLD-004",
 "phase":"F0",
 "verdict":verdict,
 "scientific_h1_adjudicated":False,
 "checks":checks,
 "candidate_results":rows,
 "next_state":"FREEZE_F1_SCORING_COHORT_BEFORE_OUTCOME_SCORING" if verdict=="FEASIBILITY_ESTABLISHED" else "DO_NOT_RUN_F1",
 "policy_authority":"NONE","runtime_permission":"NONE"
}
(ROOT/"feasibility_result.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
print(json.dumps(out,indent=2,sort_keys=True))
