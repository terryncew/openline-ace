from pathlib import Path
from hashlib import sha256
import json, sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from external_selector import strongest_comparator

P = json.loads((ROOT/"PREREGISTRATION.json").read_text())
r = json.loads((ROOT/"external_result.json").read_text())
checks = {
    "allowed_verdict": r.get("verdict") in set(P["allowed_verdicts"]),
    "prereg_hash": r.get("preregistration_sha256") == sha256((ROOT/"PREREGISTRATION.json").read_bytes()).hexdigest(),
    "source_hash": r.get("source_manifest_sha256") == sha256((ROOT/"SOURCE_MANIFEST.json").read_bytes()).hexdigest(),
    "threshold_hash": r.get("thresholds_sha256") == sha256((ROOT/"GINKGO_THRESHOLDS.json").read_bytes()).hexdigest(),
    "freeze_hash": r.get("freeze_sha256") == sha256((ROOT/"FREEZE.json").read_bytes()).hexdigest(),
    "authority_none": r.get("policy_authority") == "NONE",
    "runtime_none": r.get("runtime_permission") == "NONE",
}
if r.get("verdict") in {"EXTERNAL_ALLOCATION_ADVANTAGE_SUPPORTED", "EXTERNAL_GENERALIZATION_NOT_SUPPORTED"}:
    b = str(P["primary_budget"])
    expected_comp = strongest_comparator(r["metrics"], P["comparators"], int(P["primary_budget"]))
    checks["strongest_comparator_recomputed"] = expected_comp == r.get("strongest_comparator")
    target = r["metrics"][P["target_strategy"]]
    comp = r["metrics"][expected_comp]
    cost_ok = float(target["mean_assays_to_first_liability_positive_only"]) < float(comp["mean_assays_to_first_liability_positive_only"])
    fr_ok = float(target["budgets"][b]["false_reassurance_fraction"]) <= float(comp["budgets"][b]["false_reassurance_fraction"])
    ci_ok = float(r["paired_bootstrap"]["ci_upper"]) < 0.0
    expected_verdict = "EXTERNAL_ALLOCATION_ADVANTAGE_SUPPORTED" if cost_ok and fr_ok and ci_ok else "EXTERNAL_GENERALIZATION_NOT_SUPPORTED"
    checks["verdict_recomputed"] = expected_verdict == r["verdict"]
    checks["cohort_hash"] = r.get("external_cohort_sha256") == sha256((ROOT/"external_cohort.json").read_bytes()).hexdigest()
    checks["traces_hash"] = r.get("external_traces_sha256") == sha256((ROOT/"external_traces.jsonl").read_bytes()).hexdigest()
elif r.get("verdict") == "DATA_INSUFFICIENT":
    checks["cohort_exists"] = (ROOT/"external_cohort.json").is_file()
    checks["cohort_hash"] = r.get("external_cohort_sha256") == sha256((ROOT/"external_cohort.json").read_bytes()).hexdigest()

out={"schema":"openline.trial-selector.ginkgo.result-verification.v1","verified":all(checks.values()),"checks":checks,"verdict":r.get("verdict")}
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
