from pathlib import Path
from hashlib import sha256
import json
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
m=json.loads((ROOT/"RELEASE_MANIFEST.json").read_text())
declared={x["path"]:x for x in m["files"]}
actual={}
for rel in declared:
    p=REPO/rel
    if p.is_file():
        b=p.read_bytes()
        actual[rel]={"sha256":sha256(b).hexdigest(),"size":len(b)}
runtime={"fixture_result.json","t0_source_binding.json","t0_model.json","t0_receipts.jsonl","interventions.json","external_traces.jsonl","external_result.json"}
inside=set()
for p in ROOT.rglob("*"):
    if not p.is_file() or "__pycache__" in p.parts or p.suffix==".pyc":
        continue
    if p.name=="RELEASE_MANIFEST.json" or p.name in runtime:
        continue
    inside.add(p.relative_to(REPO).as_posix())
expected_inside={r for r in declared if r.startswith("experiments/prospective-selective-standing-001/")}
checks={
 "all_declared_present":set(actual)==set(declared),
 "experiment_closure":inside==expected_inside,
 "hashes":all(actual.get(r,{}).get("sha256")==v["sha256"] for r,v in declared.items()),
 "sizes":all(actual.get(r,{}).get("size")==v["size"] for r,v in declared.items()),
 "authority_none":m.get("policy_authority")=="NONE",
 "runtime_none":m.get("runtime_permission")=="NONE"
}
out={"schema":"openline.ace.psd001.release-verification.v1","verified":all(checks.values()),"checks":checks,"file_count":len(actual)}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
