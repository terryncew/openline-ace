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
inside=set()
for p in ROOT.rglob("*"):
    if not p.is_file() or "__pycache__" in p.parts or p.suffix==".pyc":
        continue
    if p.name in {"RELEASE_MANIFEST.json","fixture_result.json","feasibility_result.json","external_result.json"}:
        continue
    inside.add(p.relative_to(REPO).as_posix())
expected_inside={r for r in declared if r.startswith("experiments/standing-loss-lead-time-004/")}
checks={
 "all_declared_present":set(actual)==set(declared),
 "experiment_closure":inside==expected_inside,
 "hashes":all(actual.get(r,{}).get("sha256")==v["sha256"] for r,v in declared.items()),
 "sizes":all(actual.get(r,{}).get("size")==v["size"] for r,v in declared.items()),
 "authority_none":m.get("policy_authority")=="NONE",
 "runtime_none":m.get("runtime_permission")=="NONE"
}
out={"schema":"openline.ace.sld004.release-verification.v1","verified":all(checks.values()),"checks":checks,"file_count":len(actual)}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
