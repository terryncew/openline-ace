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
from sld003.core import parse_state, summarize_structure, evaluate, ts

S = json.loads((ROOT / "source_manifest.json").read_text())
P = json.loads((ROOT / "preregistration.json").read_text())
TOKEN = os.environ.get("GITHUB_TOKEN")
UA = "openline-ace-sld003"

def headers(github=False):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if github:
        h["Accept"] = "application/vnd.github+json"
        h["X-GitHub-Api-Version"] = "2022-11-28"
        if TOKEN:
            h["Authorization"] = f"Bearer {TOKEN}"
    return h

def request_json(url, *, github=False, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers(github), method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)

def request_text(url, *, github=False):
    req = urllib.request.Request(url, headers=headers(github))
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8")

def gh(url):
    return request_json(url, github=True)

def latest_commit(repo, until, path=None):
    params = {"until": until, "per_page": 1}
    if path:
        params["path"] = path
    url = f"https://api.github.com/repos/{repo}/commits?" + urllib.parse.urlencode(params)
    rows = gh(url)
    return rows[0] if rows else None

def raw(repo, ref, path):
    return request_text(f"https://raw.githubusercontent.com/{repo}/{ref}/{path}")

def osv_batch(rows):
    queries = [
        {"package": {"name": r["name"], "ecosystem": r["ecosystem"]}, "version": r["version"]}
        for r in rows
    ]
    out = []
    for start in range(0, len(queries), 400):
        payload = request_json("https://api.osv.dev/v1/querybatch", data={"queries": queries[start:start+400]})
        out.extend(payload.get("results", []))
    return out

def osv_detail(vuln_id):
    return request_json("https://api.osv.dev/v1/vulns/" + urllib.parse.quote(vuln_id, safe=""))

def vuln_ids_for_versions(rows):
    if not rows:
        return set()
    results = osv_batch(rows)
    ids = set()
    for result in results:
        for v in result.get("vulns", []) or []:
            if v.get("id"):
                ids.add(v["id"])
    return ids

def published_in_window(detail):
    published = detail.get("published")
    if not published:
        return False
    return S["event_window"]["from"] <= published <= S["event_window"]["through"]

raw_evidence = {"schema": "openline.ace.sld003.external-raw.v1", "sources": []}
events = []
structures = []
source_ok = True
detail_cache = {}
query_cache = {}

try:
    for source in S["sources"]:
        repo, lockfile, parser, ecosystem = source["repo"], source["lockfile"], source["parser"], source["ecosystem"]
        snap = latest_commit(repo, "2025-01-01T00:00:00Z", path=lockfile)
        if not snap:
            raise RuntimeError(f"no_snapshot:{repo}:{lockfile}")
        snap_sha = snap["sha"]
        snap_text = raw(repo, snap_sha, lockfile)
        snap_rows = parse_state(parser, snap_text)
        struct = summarize_structure(snap_rows)
        struct.update({"repo": repo, "ecosystem": ecosystem, "snapshot_sha": snap_sha, "lockfile": lockfile})
        structures.append(struct)

        # Candidate advisories are bound to the frozen snapshot package@version set.
        batch = osv_batch(snap_rows)
        candidates = {}
        for row, result in zip(snap_rows, batch):
            for vuln in result.get("vulns", []) or []:
                vid = vuln.get("id")
                if not vid:
                    continue
                detail = detail_cache.get(vid)
                if detail is None:
                    detail = osv_detail(vid)
                    detail_cache[vid] = detail
                if not published_in_window(detail):
                    continue
                key = (vid, row["name"])
                record = candidates.setdefault(key, {
                    "advisory_id": vid,
                    "package": row["name"],
                    "snapshot_version": row["version"],
                    "published_at": detail["published"],
                    "modified_at": detail.get("modified"),
                })
                if row["version"] < record["snapshot_version"]:
                    record["snapshot_version"] = row["version"]

        ordered = sorted(
            candidates.values(),
            key=lambda x: (x["published_at"], x["advisory_id"], x["package"], x["snapshot_version"])
        )[: int(S["max_candidate_advisories_per_source"])]

        source_raw = {
            "repo": repo,
            "ecosystem": ecosystem,
            "snapshot_sha": snap_sha,
            "structure": struct,
            "candidate_advisories": ordered,
            "events": [],
        }

        for cand in ordered:
            published = cand["published_at"]
            state_commit = latest_commit(repo, published, path=lockfile)
            if not state_commit:
                continue
            state_sha = state_commit["sha"]
            state_text = raw(repo, state_sha, lockfile)
            state_rows = parse_state(parser, state_text)
            target_rows = [r for r in state_rows if r["name"] == cand["package"]]
            cache_key = tuple((r["ecosystem"], r["name"], r["version"]) for r in target_rows)
            ids_now = query_cache.get(cache_key)
            if ids_now is None:
                ids_now = vuln_ids_for_versions(target_rows)
                query_cache[cache_key] = ids_now

            affected_rows = [r for r in target_rows if cand["advisory_id"] in vuln_ids_for_versions([r])]
            if affected_rows:
                depth = min(r["depth"] for r in affected_rows)
                classification = "TRUE_AFFECTED"
            else:
                depth = None
                classification = "STALE_WATCHLIST_CONTROL"

            event = {
                "event_id": f"{repo}:{cand['advisory_id']}:{cand['package']}",
                "repo": repo,
                "ecosystem": ecosystem,
                "lockfile": lockfile,
                "parser": parser,
                "advisory_id": cand["advisory_id"],
                "package": cand["package"],
                "published_at": published,
                "event_state_sha": state_sha,
                "classification": classification,
                "depth": depth,
                "affected_versions": sorted({r["version"] for r in affected_rows}),
                "remediation_at": None,
                "remediation_sha": None,
            }

            if classification == "TRUE_AFFECTED" and depth is not None and depth >= 2:
                params = urllib.parse.urlencode({
                    "path": lockfile,
                    "since": published,
                    "until": S["remediation_horizon"],
                    "per_page": int(S["max_lockfile_commits_per_remediation"]),
                })
                commits = gh(f"https://api.github.com/repos/{repo}/commits?{params}")
                commits = sorted(
                    commits,
                    key=lambda c: (((c.get("commit") or {}).get("committer") or {}).get("date") or "")
                )
                for commit in commits:
                    cdate = (((commit.get("commit") or {}).get("committer") or {}).get("date"))
                    if not cdate or cdate <= published:
                        continue
                    text = raw(repo, commit["sha"], lockfile)
                    rows = parse_state(parser, text)
                    targets = [r for r in rows if r["name"] == cand["package"]]
                    still = cand["advisory_id"] in vuln_ids_for_versions(targets)
                    if not still:
                        event["remediation_at"] = cdate
                        event["remediation_sha"] = commit["sha"]
                        break

            events.append(event)
            source_raw["events"].append(event)

        raw_evidence["sources"].append(source_raw)

except Exception as exc:
    source_ok = False
    raw_evidence["source_error"] = {"type": type(exc).__name__, "message": str(exc)}

result = evaluate(events, structures, P, source_ok=source_ok)

raw_path = ROOT / "external_raw.json"
events_path = ROOT / "external_events.jsonl"
result_path = ROOT / "external_result.json"
raw_path.write_text(json.dumps(raw_evidence, sort_keys=True, separators=(",", ":")) + "\n")
events_path.write_text("".join(json.dumps(e, sort_keys=True, separators=(",", ":")) + "\n" for e in events))

for label, path in [
    ("preregistration", ROOT / "preregistration.json"),
    ("source_manifest", ROOT / "source_manifest.json"),
    ("freeze", ROOT / "FREEZE.json"),
    ("external_raw", raw_path),
    ("external_events", events_path),
]:
    result[label + "_sha256"] = sha256(path.read_bytes()).hexdigest()

result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps(result, indent=2, sort_keys=True))
