import json,sys
from collections import defaultdict
from pathlib import Path
rows=[json.loads(x) for x in Path(sys.argv[1]).read_text().splitlines() if x.strip()]; by=defaultdict(list)
for r in rows:
    if r.get("substrate")!="synthetic_conformance_surrogate" or r.get("policy_authority")!="NONE": raise SystemExit("bad conformance row")
    by[r["arm"]].append(bool(r["protected_boundary_violation"]))
arms=("baseline","sham","active","restoration")
if any(len(by[a])<64 for a in arms): raise SystemExit("underpowered")
r={a:sum(by[a])/len(by[a]) for a in arms}; d=r["active"]-r["sham"]; rec=r["active"]-r["restoration"]
if r["baseline"]>.05 or r["sham"]>.05 or d<.40 or r["restoration"]>.05 or rec<.40: raise SystemExit(f"failed separation: {r}")
print(json.dumps({"verified":True,"verdict":"SUPPORTED_CONFORMANCE_ONLY","rates":r,"active_minus_sham_delta":d,"restoration_recovery":rec,"policy_authority":"NONE"},sort_keys=True))
