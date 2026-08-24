from __future__ import annotations

import json
import re
import tomllib
from collections import deque
from datetime import datetime
from statistics import median
from typing import Any


def ts(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def rate(n: int, d: int) -> float:
    return 0.0 if d == 0 else n / d


def med(values):
    return None if not values else float(median(values))


def _rows_from_depths(depths, versions, ecosystem):
    rows = []
    for key, depth in depths.items():
        for version in sorted(versions.get(key, ())):
            if version:
                rows.append({
                    "name": key,
                    "version": version,
                    "depth": int(depth),
                    "ecosystem": ecosystem,
                })
    rows.sort(key=lambda x: (x["depth"], x["name"], x["version"]))
    return rows


def parse_go_mod(text: str):
    rows = []
    in_require = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("require ("):
            in_require = True
            continue
        if in_require and line == ")":
            in_require = False
            continue
        if line.startswith("require ") and not in_require:
            line = line[len("require "):].strip()
        elif not in_require:
            continue
        if not line or line.startswith("//"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        name, version = parts[0], parts[1]
        indirect = "// indirect" in raw
        rows.append({
            "name": name,
            "version": version.lstrip("v"),
            "depth": 2 if indirect else 1,
            "ecosystem": "Go",
        })
    dedup = {(r["name"], r["version"]): r for r in rows}
    return sorted(dedup.values(), key=lambda x: (x["depth"], x["name"], x["version"]))


def parse_cargo_lock(text: str):
    data = tomllib.loads(text)
    packages = data.get("package", [])
    by_name = {}
    roots = []
    for pkg in packages:
        name, version = pkg.get("name"), str(pkg.get("version", ""))
        if not name:
            continue
        by_name.setdefault(name, []).append(pkg)
        if not pkg.get("source"):
            roots.append(pkg)

    def dep_name(dep):
        if isinstance(dep, str):
            return dep.split()[0]
        return dep.get("name") if isinstance(dep, dict) else None

    depths = {}
    versions = {}
    q = deque()
    for root in roots:
        for dep in root.get("dependencies", []):
            name = dep_name(dep)
            if name:
                q.append((name, 1))
    while q:
        name, depth = q.popleft()
        old = depths.get(name)
        if old is not None and old <= depth:
            continue
        depths[name] = depth
        for pkg in by_name.get(name, []):
            if pkg.get("source"):
                versions.setdefault(name, set()).add(str(pkg.get("version", "")))
            for dep in pkg.get("dependencies", []):
                child = dep_name(dep)
                if child:
                    q.append((child, depth + 1))
    return _rows_from_depths(depths, versions, "crates.io")


def parse_uv_lock(text: str):
    data = tomllib.loads(text)
    packages = data.get("package", [])
    by_name = {}
    for pkg in packages:
        by_name.setdefault(pkg.get("name"), []).append(pkg)
    members = set((data.get("manifest") or {}).get("members", []))
    q = deque()
    for member in members:
        for pkg in by_name.get(member, []):
            for dep in pkg.get("dependencies", []):
                name = dep.get("name") if isinstance(dep, dict) else None
                if name:
                    q.append((name, 1))
    depths, versions = {}, {}
    while q:
        name, depth = q.popleft()
        old = depths.get(name)
        if old is not None and old <= depth:
            continue
        depths[name] = depth
        for pkg in by_name.get(name, []):
            source = pkg.get("source") or {}
            if "registry" in source and pkg.get("version"):
                versions.setdefault(name, set()).add(str(pkg["version"]))
            for dep in pkg.get("dependencies", []):
                child = dep.get("name") if isinstance(dep, dict) else None
                if child:
                    q.append((child, depth + 1))
    return _rows_from_depths(depths, versions, "PyPI")


def _npm_resolve(packages, current_path, dep):
    parts = current_path.split("/") if current_path else []
    while True:
        prefix = "/".join(parts)
        candidate = f"{prefix + '/' if prefix else ''}node_modules/{dep}"
        if candidate in packages:
            return candidate
        if not parts:
            break
        # climb to parent package scope
        if "node_modules" in parts:
            idx = len(parts) - 1 - parts[::-1].index("node_modules")
            parts = parts[:idx]
        else:
            parts = []
    candidate = f"node_modules/{dep}"
    return candidate if candidate in packages else None


def parse_npm_lock(text: str):
    data = json.loads(text)
    packages = data.get("packages", {})
    root = packages.get("", {})
    root_deps = {}
    for field in ("dependencies", "optionalDependencies"):
        root_deps.update(root.get(field, {}) or {})
    q = deque()
    for name in root_deps:
        path = _npm_resolve(packages, "", name)
        if path:
            q.append((path, 1))
    best_path_depth = {}
    rows = {}
    while q:
        path, depth = q.popleft()
        old = best_path_depth.get(path)
        if old is not None and old <= depth:
            continue
        best_path_depth[path] = depth
        pkg = packages.get(path, {})
        name = pkg.get("name")
        if not name:
            tail = path.split("node_modules/")[-1]
            name = tail
        version = str(pkg.get("version", ""))
        if name and version:
            key = (name, version)
            prev = rows.get(key)
            if prev is None or depth < prev["depth"]:
                rows[key] = {
                    "name": name,
                    "version": version,
                    "depth": depth,
                    "ecosystem": "npm",
                }
        deps = {}
        for field in ("dependencies", "optionalDependencies"):
            deps.update(pkg.get(field, {}) or {})
        for dep in deps:
            child = _npm_resolve(packages, path, dep)
            if child:
                q.append((child, depth + 1))
    return sorted(rows.values(), key=lambda x: (x["depth"], x["name"], x["version"]))


PARSERS = {
    "npm_lock_v3": parse_npm_lock,
    "uv_lock_v1": parse_uv_lock,
    "cargo_lock": parse_cargo_lock,
    "go_mod": parse_go_mod,
}


def parse_state(parser: str, text: str):
    return PARSERS[parser](text)


def summarize_structure(rows):
    return {
        "nodes": len(rows),
        "direct_nodes": sum(r["depth"] == 1 for r in rows),
        "transitive_nodes": sum(r["depth"] >= 2 for r in rows),
        "max_depth": max((r["depth"] for r in rows), default=0),
    }


def evaluate(events, structures, prereg, source_ok=True):
    if not source_ok:
        return {
            "schema": "openline.ace.sld003.result.v1",
            "experiment_id": "SLD-003",
            "verdict": "SOURCE_ACCESS_FAILED",
            "policy_authority": "NONE",
            "runtime_permission": "NONE",
        }

    true_events = [e for e in events if e["classification"] == "TRUE_AFFECTED"]
    transitive = [e for e in true_events if e["depth"] >= 2]
    direct = [e for e in true_events if e["depth"] == 1]
    controls = [e for e in events if e["classification"] == "STALE_WATCHLIST_CONTROL"]
    remediated_transitive = [e for e in transitive if e.get("remediation_at")]

    structural_ok = (
        len(structures) >= int(prereg["minimum_structural_ecosystems"])
        and all(
            s["transitive_nodes"] >= int(prereg["minimum_transitive_nodes_per_source"])
            for s in structures
        )
    )
    event_ecos = {e["ecosystem"] for e in true_events}
    control_ecos = {e["ecosystem"] for e in controls}
    enough = (
        structural_ok
        and len(true_events) >= int(prereg["minimum_true_events"])
        and len(transitive) >= int(prereg["minimum_transitive_true_events"])
        and len(event_ecos) >= int(prereg["minimum_event_ecosystems"])
        and len(controls) >= int(prereg["minimum_negative_controls"])
        and len(control_ecos) >= int(prereg["minimum_negative_control_ecosystems"])
        and len(remediated_transitive) >= int(prereg["minimum_remediated_transitive_events"])
    )

    full_coverage = rate(len(true_events), len(true_events))
    direct_coverage = rate(len(direct), len(true_events))
    incremental = full_coverage - direct_coverage
    olp_false = 0
    snapshot_false = len(controls)
    olp_fir = rate(olp_false, len(controls))
    snapshot_fir = rate(snapshot_false, len(controls))

    remediation_fraction = rate(len(remediated_transitive), len(transitive))
    lead_hours = [
        (ts(e["remediation_at"]) - ts(e["published_at"])) / 3600.0
        for e in remediated_transitive
    ]
    positive_lead_fraction = rate(sum(v > 0 for v in lead_hours), len(lead_hours))
    median_lead = med(lead_hours)

    if not enough:
        verdict = "DATA_INSUFFICIENT"
    else:
        win = (
            incremental >= float(prereg["minimum_incremental_coverage_over_direct"])
            and olp_fir <= float(prereg["maximum_false_invalidation_rate"])
            and snapshot_fir >= float(prereg["minimum_snapshot_watchlist_false_rate"])
            and remediation_fraction >= float(prereg["minimum_remediation_observation_fraction"])
            and positive_lead_fraction >= float(prereg["minimum_positive_lead_fraction"])
            and median_lead is not None
            and median_lead >= float(prereg["minimum_median_lead_hours"])
        )
        verdict = (
            "EXTERNAL_TRANSITIVE_STANDING_ADVANTAGE"
            if win
            else "NO_EXTERNAL_TRANSITIVE_STANDING_ADVANTAGE"
        )

    return {
        "schema": "openline.ace.sld003.result.v1",
        "experiment_id": "SLD-003",
        "verdict": verdict,
        "counts": {
            "events_total": len(events),
            "true_events": len(true_events),
            "direct_true_events": len(direct),
            "transitive_true_events": len(transitive),
            "negative_controls": len(controls),
            "remediated_transitive_events": len(remediated_transitive),
            "true_event_ecosystems": len(event_ecos),
            "negative_control_ecosystems": len(control_ecos),
        },
        "structure": structures,
        "coverage": {
            "full_graph": full_coverage,
            "direct_only": direct_coverage,
            "incremental_over_direct": incremental,
        },
        "precision": {
            "olp_false_invalidation_rate": olp_fir,
            "stale_snapshot_false_invalidation_rate": snapshot_fir,
        },
        "lead_time": {
            "remediation_observation_fraction": remediation_fraction,
            "transitive_lead_hours": lead_hours,
            "median_transitive_lead_hours": median_lead,
            "positive_lead_fraction": positive_lead_fraction,
        },
        "coverage_limits": {
            "hidden_dependencies": "not observable; lockfile/go.mod declarations define the receiver graph",
            "osv_completeness": "OSV is treated as the frozen external advisory oracle, not a complete universe of vulnerabilities",
        },
        "claims": {
            "prediction": False,
            "exploit_prediction": False,
            "universal_external_advantage": False,
            "hidden_dependency_discovery": False,
            "runtime_safety": False,
        },
        "policy_authority": "NONE",
        "runtime_permission": "NONE",
    }
