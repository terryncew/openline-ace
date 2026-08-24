from pathlib import Path
from hashlib import sha256
import json

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
m=json.loads((ROOT/"RELEASE_MANIFEST.json").read_text())
expected={x["path"]:x for x in m["files"]}
actual={}
for rel,item in expected.items():
    p=REPO/rel
    if p.is_file():
        b=p.read_bytes()
        actual[rel]={"sha256":sha256(b).hexdigest(),"size":len(b)}
inside=set()
for p in ROOT.rglob("*"):
    if not p.is_file() or "__pycache__" in p.parts or p.suffix==".pyc" or p.name=="RELEASE_MANIFEST.json":
        continue
    if p.name in {"external_raw.json","external_events.jsonl","external_result.json"}:
        continue
    inside.add(p.relative_to(REPO).as_posix())
expected_inside={r for r in expected if r.startswith("experiments/standing-loss-lead-time-003/")}
checks={
    "all_declared_present":set(actual)==set(expected),
    "experiment_closure":inside==expected_inside,
    "hashes":all(actual.get(r,{}).get("sha256")==i["sha256"] for r,i in expected.items()),
    "sizes":all(actual.get(r,{}).get("size")==i["size"] for r,i in expected.items()),
    "authority_none":m.get("policy_authority")=="NONE",
    "runtime_none":m.get("runtime_permission")=="NONE",
}
out={"schema":"openline.ace.sld003.release-verification.v1","verified":all(checks.values()),"checks":checks,"file_count":len(actual)}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["verified"] else 2)
