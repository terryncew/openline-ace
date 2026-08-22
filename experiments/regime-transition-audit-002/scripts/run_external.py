from __future__ import annotations
from pathlib import Path
import json, os, sys, urllib.parse, urllib.request, hashlib, time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rta002.core import build_case, evaluate

TOKEN=os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    raise SystemExit("GITHUB_TOKEN required")

source=json.loads((ROOT/"source_manifest.json").read_text())
prereg=json.loads((ROOT/"preregistration.json").read_text())
repo=source["source"]["repository"]
owner,name=repo.split("/")
window=source["source"]["query_window"]
max_prs=int(source["source"]["max_prs"])

headers={
    "Accept":"application/vnd.github+json",
    "Authorization":f"Bearer {TOKEN}",
    "X-GitHub-Api-Version":"2022-11-28",
    "User-Agent":"openline-ace-rta002"
}

def get(url):
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.load(r)

q=f"repo:{repo} is:pr is:merged merged:{window['merged_from'][:10]}..{window['merged_through'][:10]}"
search="https://api.github.com/search/issues?"+urllib.parse.urlencode({
    "q":q,"sort":"created","order":"asc","per_page":100
})
items=get(search)["items"][:max_prs]
raw=[]; cases=[]
for item in items:
    n=item["number"]
    pr=get(f"https://api.github.com/repos/{owner}/{name}/pulls/{n}")
    reviews=get(f"https://api.github.com/repos/{owner}/{name}/pulls/{n}/reviews?per_page=100")
    commits=get(f"https://api.github.com/repos/{owner}/{name}/pulls/{n}/commits?per_page=100")
    raw.append({"pr":pr,"reviews":reviews,"commits":commits})
    case=build_case(pr,reviews,commits,prereg)
    if case is not None:
        cases.append(case)

raw_path=ROOT/"external_raw.json"
raw_path.write_text(json.dumps(raw,sort_keys=True,separators=(",",":"))+"\n")
cases_path=ROOT/"external_cases.jsonl"
cases_path.write_text("".join(json.dumps(c,sort_keys=True)+"\n" for c in cases))
result=evaluate(cases,prereg)
result.update({
    "source_manifest_sha256":hashlib.sha256((ROOT/"source_manifest.json").read_bytes()).hexdigest(),
    "preregistration_sha256":hashlib.sha256((ROOT/"preregistration.json").read_bytes()).hexdigest(),
    "external_raw_sha256":hashlib.sha256(raw_path.read_bytes()).hexdigest(),
    "external_cases_sha256":hashlib.sha256(cases_path.read_bytes()).hexdigest(),
    "source_repository":repo,
    "source_query":q
})
(ROOT/"external_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2,sort_keys=True))
