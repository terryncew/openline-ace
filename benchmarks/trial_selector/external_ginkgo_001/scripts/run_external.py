from __future__ import annotations

from pathlib import Path
from hashlib import sha1, sha256
import csv
import io
import json
import math
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
sys.path.insert(0, str(ROOT))
from external_selector import Threshold, run_leave_one_out, adjudicate

P = json.loads((ROOT / "PREREGISTRATION.json").read_text())
S = json.loads((ROOT / "SOURCE_MANIFEST.json").read_text())
T = json.loads((ROOT / "GINKGO_THRESHOLDS.json").read_text())


def write_terminal(verdict, detail):
    result = {
        "schema": "openline.trial-selector.ginkgo.result.v1",
        "experiment_id": P["experiment_id"],
        "verdict": verdict,
        "detail": detail,
        "policy_authority": "NONE",
        "runtime_permission": "NONE",
    }
    for label, path in [("preregistration", ROOT/"PREREGISTRATION.json"), ("source_manifest", ROOT/"SOURCE_MANIFEST.json"), ("thresholds", ROOT/"GINKGO_THRESHOLDS.json"), ("freeze", ROOT/"FREEZE.json")]:
        result[label + "_sha256"] = sha256(path.read_bytes()).hexdigest()
    (ROOT / "external_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def git_blob_sha1(data):
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

try:
    req = urllib.request.Request(S["raw_url"], headers={"User-Agent": "openline-trial-selector-ginkgo-ext-001"})
    with urllib.request.urlopen(req, timeout=60) as response:
        raw = response.read()
except Exception as exc:
    write_terminal("SOURCE_ACCESS_FAILED", {"type": type(exc).__name__, "message": str(exc)})
    raise SystemExit(0)

binding = {
    "size_bytes": len(raw),
    "expected_size_bytes": int(S["size_bytes"]),
    "git_blob_sha1": git_blob_sha1(raw),
    "expected_git_blob_sha1": S["git_blob_sha1"],
}
# Store SHA-256 separately without abusing path helper.
binding["sha256"] = sha256_bytes = __import__("hashlib").sha256(raw).hexdigest()
if len(raw) != int(S["size_bytes"]) or binding["git_blob_sha1"] != S["git_blob_sha1"]:
    write_terminal("SOURCE_BINDING_FAILED", binding)
    raise SystemExit(0)

try:
    text = raw.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
except Exception as exc:
    write_terminal("SOURCE_BINDING_FAILED", {"reason": "csv_parse", "type": type(exc).__name__, "message": str(exc), **binding})
    raise SystemExit(0)

required = [S["candidate_id_column"], *T["assay_order"]]
missing_columns = [c for c in required if c not in (rows[0].keys() if rows else [])]
if missing_columns:
    write_terminal("SOURCE_BINDING_FAILED", {"reason": "missing_columns", "columns": missing_columns, **binding})
    raise SystemExit(0)

jain_path = REPO / S["identity_exclusion"]["jain_canonical_path"]
jain = json.loads(jain_path.read_text())
jain_ids = {str(x).strip().casefold() for x in jain["candidate_ids"]}

def number(value):
    try:
        x = float(str(value).strip())
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None

candidates = []
excluded_overlap = []
excluded_missing = []
seen = set()
for row in rows:
    raw_name = str(row.get(S["candidate_id_column"], "")).strip()
    norm = raw_name.casefold()
    if not raw_name:
        excluded_missing.append({"candidate_id": raw_name, "reason": "missing_identity"})
        continue
    if norm in jain_ids:
        excluded_overlap.append(raw_name)
        continue
    vals = {assay: number(row.get(assay)) for assay in T["assay_order"]}
    if any(vals[a] is None for a in T["assay_order"]):
        excluded_missing.append({"candidate_id": raw_name, "reason": "incomplete_assays"})
        continue
    if norm in seen:
        write_terminal("SOURCE_BINDING_FAILED", {"reason": "duplicate_normalized_candidate", "candidate_id": raw_name, **binding})
        raise SystemExit(0)
    seen.add(norm)
    candidates.append({"candidate_id": raw_name, "assays": vals})

threshold_map = {a: Threshold(T["assays"][a]["operator"], float(T["assays"][a]["threshold"])) for a in T["assay_order"]}
from external_selector import build_matrices
values, flags = build_matrices(candidates, T["assay_order"], threshold_map)
positive = [cid for cid in values if any(flags[cid].values())]
negative = [cid for cid in values if not any(flags[cid].values())]
cohort = {
    "schema": "openline.trial-selector.ginkgo.cohort.v1",
    "source_row_count": len(rows),
    "complete_disjoint_candidate_count": len(candidates),
    "liability_positive_count": len(positive),
    "liability_negative_count": len(negative),
    "jain_overlap_excluded_count": len(excluded_overlap),
    "incomplete_excluded_count": len(excluded_missing),
    "candidate_ids": sorted(values),
    "source_binding": binding,
    "policy_authority": "NONE",
    "runtime_permission": "NONE",
}
(ROOT / "external_cohort.json").write_text(json.dumps(cohort, indent=2, sort_keys=True) + "\n")

enough = (
    len(candidates) >= int(P["minimum_complete_candidates"])
    and len(positive) >= int(P["minimum_liability_positive_candidates"])
    and len(negative) >= int(P["minimum_liability_negative_candidates"])
)
if not enough:
    result = write_terminal("DATA_INSUFFICIENT", {"cohort": cohort})
    result["external_cohort_sha256"] = __import__("hashlib").sha256((ROOT/"external_cohort.json").read_bytes()).hexdigest()
    (ROOT/"external_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    raise SystemExit(0)

run = run_leave_one_out(candidates, T["assay_order"], threshold_map, tuple(P["budgets"]))
adj = adjudicate(run, P)

trace_path = ROOT / "external_traces.jsonl"
with trace_path.open("w", encoding="utf-8") as handle:
    for strategy in sorted(run["traces"]):
        for trace in run["traces"][strategy]:
            handle.write(json.dumps({"strategy": strategy, **trace}, sort_keys=True, separators=(",", ":")) + "\n")

result = {
    "schema": "openline.trial-selector.ginkgo.result.v1",
    "experiment_id": P["experiment_id"],
    **adj,
    "cohort": cohort,
    "metrics": run["metrics"],
    "claims": {
        "therapeutic_efficacy_prediction": False,
        "clinical_success_prediction": False,
        "promotion_authority": False,
        "external_allocation_generalization": adj["verdict"] == "EXTERNAL_ALLOCATION_ADVANTAGE_SUPPORTED",
    },
    "policy_authority": "NONE",
    "runtime_permission": "NONE",
}
for label, path in [("preregistration", ROOT/"PREREGISTRATION.json"), ("source_manifest", ROOT/"SOURCE_MANIFEST.json"), ("thresholds", ROOT/"GINKGO_THRESHOLDS.json"), ("freeze", ROOT/"FREEZE.json"), ("external_cohort", ROOT/"external_cohort.json"), ("external_traces", trace_path)]:
    result[label + "_sha256"] = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
(ROOT / "external_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps(result, indent=2, sort_keys=True))
