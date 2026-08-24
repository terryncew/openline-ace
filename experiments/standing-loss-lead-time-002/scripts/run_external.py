from __future__ import annotations

from pathlib import Path
from hashlib import sha256
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sld002.core import build_case, evaluate

S = json.loads((ROOT / "source_manifest.json").read_text())
P = json.loads((ROOT / "preregistration.json").read_text())
TOKEN = os.environ.get("GITHUB_TOKEN")
UA = "openline-ace-sld002"


def _headers(auth: bool) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": UA,
    }
    if auth and TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    return headers


def get(url: str):
    last = None
    attempts = [True, False] if TOKEN else [False]
    for auth in attempts:
        request = urllib.request.Request(url, headers=_headers(auth))
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            last = exc
            if auth and exc.code in {401, 403, 404}:
                continue
            raise
    raise last or RuntimeError("source_access_failed")


def search(repo: str, stratum: dict):
    query = stratum["query_template"].format(repo=repo)
    params = urllib.parse.urlencode(
        {
            "q": query,
            "sort": stratum["sort"],
            "order": stratum["order"],
            "per_page": stratum["max_items_per_repository"],
        }
    )
    payload = get("https://api.github.com/search/issues?" + params)
    return payload.get("items", [])[: int(stratum["max_items_per_repository"])]


raw = {
    "schema": "openline.ace.sld002.external-raw.v1",
    "searches": [],
    "histories": [],
}
candidates = []
source_ok = True

try:
    for repo in S["repositories"]:
        for stratum in S["strata"]:
            items = search(repo, stratum)
            raw["searches"].append(
                {
                    "repository": repo,
                    "stratum": stratum["name"],
                    "items": items,
                }
            )
            for item in items:
                candidates.append(
                    {
                        "repository": repo,
                        "number": int(item["number"]),
                        "stratum": stratum["name"],
                        "closed_at": item.get("closed_at"),
                    }
                )
except Exception as exc:
    source_ok = False
    raw["source_error"] = {
        "type": type(exc).__name__,
        "message": str(exc),
    }

# Source manifest lists terminal first; terminal stratum wins any duplicate.
seen = set()
unique = []
for candidate in candidates:
    key = (candidate["repository"], candidate["number"])
    if key not in seen:
        seen.add(key)
        unique.append(candidate)

cases = []
if source_ok:
    try:
        for candidate in unique:
            repo = candidate["repository"]
            number = candidate["number"]
            reviews = get(
                f"https://api.github.com/repos/{repo}/pulls/{number}/reviews"
                f"?per_page={int(S['reviews_per_pr_max'])}"
            )
            commits = get(
                f"https://api.github.com/repos/{repo}/pulls/{number}/commits"
                f"?per_page={int(S['commits_per_pr_max'])}"
            )
            candidate["history_truncated"] = (
                len(reviews) >= int(S["reviews_per_pr_max"])
                or len(commits) >= int(S["commits_per_pr_max"])
            )
            raw["histories"].append(
                {
                    "candidate": dict(candidate),
                    "reviews": reviews,
                    "commits": commits,
                }
            )
            cases.append(build_case(candidate, reviews, commits))
    except Exception as exc:
        source_ok = False
        raw["source_error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

result = evaluate(cases, P, source_access_ok=source_ok)
raw_path = ROOT / "external_raw.json"
cases_path = ROOT / "external_cases.jsonl"
result_path = ROOT / "external_result.json"

raw_path.write_text(
    json.dumps(raw, sort_keys=True, separators=(",", ":")) + "\n"
)
cases_path.write_text(
    "".join(
        json.dumps(case, sort_keys=True, separators=(",", ":")) + "\n"
        for case in cases
    )
)

for label, path in [
    ("preregistration", ROOT / "preregistration.json"),
    ("source_manifest", ROOT / "source_manifest.json"),
    ("freeze", ROOT / "FREEZE.json"),
    ("external_raw", raw_path),
    ("external_cases", cases_path),
]:
    result[label + "_sha256"] = sha256(path.read_bytes()).hexdigest()

result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps(result, indent=2, sort_keys=True))
