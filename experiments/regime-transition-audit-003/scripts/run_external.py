
from pathlib import Path
from datetime import datetime, timezone
import json, os, sys, urllib.parse, urllib.request, hashlib
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from rta003.core import evaluate
T=os.environ.get("GITHUB_TOKEN")
if not T: raise SystemExit("GITHUB_TOKEN required")
S=json.loads((ROOT/"source_manifest.json").read_text()); P=json.loads((ROOT/"preregistration.json").read_text())
H={"Accept":"application/vnd.github+json","Authorization":f"Bearer {T}","X-GitHub-Api-Version":"2022-11-28","User-Agent":"openline-ace-rta003"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=30) as r: return json.load(r)
def ts(x): return datetime.fromisoformat(x.replace("Z","+00:00")).timestamp()
raw=[]; cases=[]
for repo in S["repositories"]:
    owner,name=repo.split("/")
    w=S["query_window"]
    q=f"repo:{repo} is:pr is:merged merged:{w['merged_from'][:10]}..{w['merged_through'][:10]}"
    u="https://api.github.com/search/issues?"+urllib.parse.urlencode({"q":q,"sort":"created","order":"asc","per_page":100})
    items=get(u)["items"][:S["max_prs_per_repository"]]
    for item in items:
        n=item["number"]
        pr=get(f"https://api.github.com/repos/{repo}/pulls/{n}")
        reviews=get(f"https://api.github.com/repos/{repo}/pulls/{n}/reviews?per_page=100")
        commits=get(f"https://api.github.com/repos/{repo}/pulls/{n}/commits?per_page=100")
        raw.append({"repository":repo,"pr":pr,"reviews":reviews,"commits":commits})
        approvals=sorted([r for r in reviews if r.get("state")=="APPROVED" and r.get("submitted_at")],key=lambda r:r["submitted_at"])
        if not approvals: continue
        first=ts(approvals[0]["submitted_at"]); cp=first+86400
        if pr.get("closed_at") and ts(pr["closed_at"])<=cp: continue
        pre=[r for r in reviews if r.get("submitted_at") and ts(r["submitted_at"])<=cp]
        decisive=[r for r in pre if r.get("state") in {"APPROVED","CHANGES_REQUESTED","DISMISSED"}]
        if not decisive or not any(r.get("state")=="APPROVED" for r in pre): continue
        latest=max(ts(r["submitted_at"]) for r in pre if r.get("state")=="APPROVED")
        age=min(1,max(0,(cp-latest)/3600/168))
        first_dec=min(ts(r["submitted_at"]) for r in decisive)
        ctimes=[ts(c["commit"]["committer"]["date"]) for c in commits if c.get("commit",{}).get("committer",{}).get("date")]
        churn=min(1,sum(first_dec<t<=cp for t in ctimes)/4)
        contradiction=sum(r.get("state")=="CHANGES_REQUESTED" for r in decisive)/len(decisive)
        withdrawal=sum(r.get("state")=="DISMISSED" for r in decisive)/len(decisive)
        post=[r for r in reviews if r.get("submitted_at") and ts(r["submitted_at"])>cp]
        fail=any(r.get("state") in {"CHANGES_REQUESTED","DISMISSED"} for r in post)
        cases.append({"case_id":n,"repository":repo,"checkpoint":datetime.fromtimestamp(cp,timezone.utc).isoformat().replace("+00:00","Z"),
          "age_since_last_verification":age,"dependency_churn":churn,"contradiction_rate":contradiction,
          "support_withdrawal_rate":withdrawal,"later_standing_failure":fail,"provenance":"external_github_review_history"})
rp=ROOT/"external_raw.json"; cp=ROOT/"external_cases.jsonl"
rp.write_text(json.dumps(raw,sort_keys=True,separators=(",",":"))+"\n")
cp.write_text("".join(json.dumps(x,sort_keys=True)+"\n" for x in cases))
result=evaluate(cases,P)
for name,path in [("source_manifest",ROOT/"source_manifest.json"),("preregistration",ROOT/"preregistration.json"),("external_raw",rp),("external_cases",cp)]:
    result[name+"_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
(ROOT/"external_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2,sort_keys=True))
