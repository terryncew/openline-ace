from __future__ import annotations
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys, tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from psd001.core import (
    parse_metadata, build_t0_model, intervention_seed, select_interventions,
    run_trial, adjudicate
)
from psd001.oracle import decision_truth

P=json.loads((ROOT/"preregistration.json").read_text())
S=json.loads((ROOT/"source_manifest.json").read_text())
F=json.loads((ROOT/"FREEZE.json").read_text())

def hbytes(b): return hashlib.sha256(b).hexdigest()
def hfile(p): return hbytes(Path(p).read_bytes())
def write_result(verdict, detail):
    result={
      "schema":"openline.ace.psd001.result.v1","experiment_id":"PSD-001",
      "verdict":verdict,"detail":detail,
      "preregistration_sha256":hfile(ROOT/"preregistration.json"),
      "source_manifest_sha256":hfile(ROOT/"source_manifest.json"),
      "freeze_sha256":hfile(ROOT/"FREEZE.json"),
      "policy_authority":"NONE","runtime_permission":"NONE"
    }
    (ROOT/"external_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))
    return result

tmp=Path(tempfile.mkdtemp(prefix="psd001-upstream-"))
repo=tmp/"uv"
try:
    subprocess.run(["git","init",str(repo)],check=True,capture_output=True,text=True)
    subprocess.run(["git","-C",str(repo),"remote","add","origin",S["external_substrate"]["clone_url"]],check=True,capture_output=True,text=True)
    subprocess.run(["git","-C",str(repo),"fetch","--depth","1","origin",S["external_substrate"]["commit"]],check=True,capture_output=True,text=True,timeout=180)
    subprocess.run(["git","-C",str(repo),"checkout","--detach","FETCH_HEAD"],check=True,capture_output=True,text=True)
except Exception as exc:
    write_result("SOURCE_ACCESS_FAILED",{"stage":"git_checkout","type":type(exc).__name__,"message":str(exc)})
    raise SystemExit(0)

head=subprocess.run(["git","-C",str(repo),"rev-parse","HEAD"],check=True,capture_output=True,text=True).stdout.strip()
if head != S["external_substrate"]["commit"]:
    write_result("SOURCE_BINDING_FAILED",{"stage":"commit_binding","actual":head,"expected":S["external_substrate"]["commit"]})
    raise SystemExit(0)

try:
    cp=subprocess.run(
      ["cargo","metadata","--format-version","1","--locked"],
      cwd=repo,check=True,capture_output=True,text=True,timeout=300
    )
    metadata=json.loads(cp.stdout)
except Exception as exc:
    write_result("SOURCE_ACCESS_FAILED",{"stage":"cargo_metadata","type":type(exc).__name__,"message":str(exc)})
    raise SystemExit(0)

try:
    projection=parse_metadata(metadata,S["target_crates"])
except Exception as exc:
    write_result("SOURCE_BINDING_FAILED",{"stage":"metadata_projection","type":type(exc).__name__,"message":str(exc)})
    raise SystemExit(0)

def tree_hash(paths):
    digest=hashlib.sha256()
    for p in sorted(paths):
        if not p.is_file(): continue
        rel=p.relative_to(repo).as_posix().encode()
        digest.update(len(rel).to_bytes(8,"big")); digest.update(rel)
        b=p.read_bytes(); digest.update(len(b).to_bytes(8,"big")); digest.update(b)
    return digest.hexdigest()

source_hashes={}
for target in S["target_crates"]:
    crate_dir=repo/"crates"/target
    if not crate_dir.is_dir():
        write_result("SOURCE_BINDING_FAILED",{"stage":"target_directory","missing":target})
        raise SystemExit(0)
    files=[repo/"Cargo.toml",repo/"Cargo.lock",*list(crate_dir.rglob("*"))]
    source_hashes[target]=tree_hash(files)

# One real build check for all six frozen targets.
build_cmd=["cargo","check","--locked"]
for t in S["target_crates"]:
    build_cmd += ["-p",t]
try:
    build=subprocess.run(build_cmd,cwd=repo,capture_output=True,text=True,timeout=1800)
except Exception as exc:
    write_result("SOURCE_BUILD_FAILED",{"stage":"cargo_check","type":type(exc).__name__,"message":str(exc)})
    raise SystemExit(0)
if build.returncode != 0:
    write_result("SOURCE_BUILD_FAILED",{
      "stage":"cargo_check","returncode":build.returncode,
      "stdout_tail":build.stdout[-6000:],"stderr_tail":build.stderr[-6000:]
    })
    raise SystemExit(0)

t0=build_t0_model(projection,S["target_crates"],True,source_hashes)
if len(t0["decisions"]) != S["expected_t0_decision_count"]:
    write_result("SOURCE_BINDING_FAILED",{"stage":"decision_count","count":len(t0["decisions"])})
    raise SystemExit(0)

# Bind the exact upstream material before selecting an intervention.
binding={
  "upstream_commit":head,
  "cargo_metadata_sha256":hbytes(json.dumps(metadata,sort_keys=True,separators=(",",":")).encode()),
  "target_source_hashes":source_hashes,
  "t0_model_sha256":t0["model_sha256"],
  "cargo_check_command":build_cmd,
  "cargo_check_returncode":build.returncode,
}
(ROOT/"t0_source_binding.json").write_text(json.dumps(binding,indent=2,sort_keys=True)+"\n")
(ROOT/"t0_model.json").write_text(json.dumps(t0,indent=2,sort_keys=True)+"\n")
with (ROOT/"t0_receipts.jsonl").open("w") as f:
    for r in t0["receipts"]:
        f.write(json.dumps(r,sort_keys=True,separators=(",",":"))+"\n")

membership={}
for c in set().union(*(set(v) for v in projection["union"].values())):
    membership[c]=sum(c in projection["union"][t] for t in S["target_crates"])
pool={
  "shared":sum(n>=2 for n in membership.values()),
  "single":sum(n==1 for n in membership.values()),
  "absent":len(projection["absent_components"]),
}
counts={
 "shared":P["intervention_selector"]["normal_shared_component_trials"],
 "single":P["intervention_selector"]["normal_single_target_component_trials"],
 "absent":P["intervention_selector"]["absent_component_controls"],
 "missing_edge":P["intervention_selector"]["known_missing_edge_trials"],
}
seed=intervention_seed("PSD-001",S["external_substrate"]["commit"],hfile(ROOT/"FREEZE.json"))
try:
    trials=select_interventions(projection,S["target_crates"],seed,counts)
except Exception as exc:
    result=write_result("DATA_INSUFFICIENT",{"stage":"intervention_pool","pool":pool,"type":type(exc).__name__,"message":str(exc)})
    result["source_binding_sha256"]=hfile(ROOT/"t0_source_binding.json")
    result["t0_model_sha256"]=hfile(ROOT/"t0_model.json")
    (ROOT/"external_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    raise SystemExit(0)

(ROOT/"interventions.json").write_text(json.dumps({
  "schema":"openline.ace.psd001.interventions.v1",
  "seed":seed,"pool":pool,"trials":trials,
  "selector_has_seen_propagation_outputs":False
},indent=2,sort_keys=True)+"\n")

traces=[]
for trial in trials:
    tr=run_trial(t0,trial)
    # independent oracle cross-check: fail binding if two implementations disagree.
    independent=decision_truth(t0,trial["component_id"])
    if independent != tr["ground_truth"]:
        write_result("SOURCE_BINDING_FAILED",{"stage":"oracle_independence_crosscheck","trial_id":trial["trial_id"]})
        raise SystemExit(0)
    traces.append(tr)

with (ROOT/"external_traces.jsonl").open("w") as f:
    for tr in traces:
        f.write(json.dumps(tr,sort_keys=True,separators=(",",":"))+"\n")

adj=adjudicate(t0,traces,pool,P)
result={
  "schema":"openline.ace.psd001.result.v1","experiment_id":"PSD-001",
  **adj,
  "external_substrate":S["external_substrate"],
  "target_crates":S["target_crates"],
  "t0_decision_count":len(t0["decisions"]),
  "trial_count":len(trials),
  "claims":{
    "selective_localization":adj["verdict"]=="SELECTIVE_LOCALIZATION_ADVANTAGE",
    "early_warning":False,"minimal_intervention":False,"fast_selection":False,
    "algorithmic_graph_superiority_over_equivalent_index":False,
  },
  "policy_authority":"NONE","runtime_permission":"NONE",
}
for label,path in [
 ("preregistration",ROOT/"preregistration.json"),
 ("source_manifest",ROOT/"source_manifest.json"),
 ("freeze",ROOT/"FREEZE.json"),
 ("source_binding",ROOT/"t0_source_binding.json"),
 ("t0_model",ROOT/"t0_model.json"),
 ("t0_receipts",ROOT/"t0_receipts.jsonl"),
 ("interventions",ROOT/"interventions.json"),
 ("external_traces",ROOT/"external_traces.jsonl"),
]:
    result[label+"_sha256"]=hfile(path)
(ROOT/"external_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2,sort_keys=True))
