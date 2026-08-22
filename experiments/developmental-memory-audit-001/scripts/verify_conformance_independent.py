from __future__ import annotations
import json, sys
from collections import defaultdict
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "fixtures/conformance-results.jsonl")
rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
g = defaultdict(lambda: defaultdict(list))
for r in rows:
    g[r["candidate_id"]][r["arm"]].append(bool(r["success"]))

def rate(xs):
    return sum(xs) / len(xs)

verdicts = {}
for cid, arms in sorted(g.items()):
    if any(len(arms.get(a, [])) < 8 for a in ("baseline","sham","active","restoration")):
        verdicts[cid] = "INCOMPLETE"
        continue
    s = {a: rate(arms[a]) for a in ("baseline","sham","active","restoration")}
    delta = (1-s["active"]) - (1-s["sham"])
    recovery = s["restoration"] - s["active"]
    if s["baseline"] < .75:
        v = "ABSTAIN_BASELINE_UNSTABLE"
    elif s["sham"] < .75:
        v = "ABSTAIN_SHAM_DAMAGE"
    elif delta < .40:
        v = "REJECTED_RITUAL"
    elif recovery < .40:
        v = "UNRESOLVED_NO_RECOVERY"
    else:
        v = "SUPPORTED_LOAD_BEARING"
    verdicts[cid] = v

expected = {
    "planted.load_bearing": "SUPPORTED_LOAD_BEARING",
    "planted.ritual": "REJECTED_RITUAL",
    "planted.sham_sensitive": "ABSTAIN_SHAM_DAMAGE",
    "planted.no_restoration": "INCOMPLETE",
}
if verdicts != expected:
    raise SystemExit(f"independent verification mismatch: {verdicts}")
print(json.dumps({"verified": True, "verdicts": verdicts, "policy_authority": "NONE"}, sort_keys=True))
