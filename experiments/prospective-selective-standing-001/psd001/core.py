from __future__ import annotations

from collections import defaultdict, deque
import hashlib
import json
import math
import random
from typing import Any

KINDS = ("runtime", "build", "dev")
DECISION_TYPES = (
    "runtime_security_acceptance",
    "build_security_acceptance",
    "test_security_acceptance",
    "build_acceptance",
    "promotion_permission",
)
SECURITY_DECISION_BY_KIND = {
    "runtime": "runtime_security_acceptance",
    "build": "build_security_acceptance",
    "dev": "test_security_acceptance",
}
PRIMARY_STRATEGIES = (
    "openline_evidence_graph",
    "artifact_component_join",
    "repo_scope_join",
    "decision_closure_index",
    "headline_only",
)

class PSD001Error(ValueError):
    pass

def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def digest_obj(obj: Any) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()

def package_component_id(package: dict[str, Any]) -> str:
    source = package.get("source")
    if not source:
        raise PSD001Error("workspace_package_has_no_external_component_id")
    return f'{package["name"]}@{package["version"]}|{source}'

def parse_metadata(metadata: dict[str, Any], targets: list[str]) -> dict[str, Any]:
    packages = {p["id"]: p for p in metadata.get("packages", [])}
    name_to_ids = defaultdict(list)
    for pid, p in packages.items():
        name_to_ids[p["name"]].append(pid)

    for target in targets:
        ids = name_to_ids.get(target, [])
        if len(ids) != 1:
            raise PSD001Error(f"target_resolution:{target}:{len(ids)}")

    resolve = metadata.get("resolve") or {}
    nodes = {n["id"]: n for n in resolve.get("nodes", [])}
    if not nodes:
        raise PSD001Error("missing_resolve_nodes")

    adjacency = defaultdict(list)
    for pid, node in nodes.items():
        for dep in node.get("deps", []):
            dep_id = dep["pkg"]
            dep_kinds = dep.get("dep_kinds") or [{"kind": None, "target": None}]
            kinds = set()
            for dk in dep_kinds:
                k = dk.get("kind")
                if k is None:
                    kinds.add("runtime")
                elif k == "build":
                    kinds.add("build")
                elif k == "dev":
                    kinds.add("dev")
                else:
                    kinds.add("runtime")
            adjacency[pid].append((dep_id, tuple(sorted(kinds))))

    target_ids = {t: name_to_ids[t][0] for t in targets}
    closures: dict[str, dict[str, set[str]]] = {
        t: {k: set() for k in KINDS} for t in targets
    }
    union: dict[str, set[str]] = {t: set() for t in targets}

    # Classification is by the kind on the first edge leaving the frozen target.
    # Descendants of that first-edge dependency inherit that root-use class.
    for target, root_id in target_ids.items():
        for dep_id, first_kinds in adjacency.get(root_id, []):
            for root_kind in first_kinds:
                q = deque([dep_id])
                seen = set()
                while q:
                    cur = q.popleft()
                    if cur in seen:
                        continue
                    seen.add(cur)
                    p = packages.get(cur)
                    if p and p.get("source"):
                        cid = package_component_id(p)
                        closures[target][root_kind].add(cid)
                        union[target].add(cid)
                    for nxt, _edge_kinds in adjacency.get(cur, []):
                        if nxt not in seen:
                            q.append(nxt)

    all_external = {
        package_component_id(p)
        for p in packages.values()
        if p.get("source")
    }
    selected_union = set().union(*(union[t] for t in targets))
    absent = all_external - selected_union

    return {
        "closures": {t: {k: sorted(v) for k, v in ks.items()} for t, ks in closures.items()},
        "union": {t: sorted(v) for t, v in union.items()},
        "all_external_components": sorted(all_external),
        "absent_components": sorted(absent),
        "target_package_ids": target_ids,
    }

def build_t0_model(projection: dict[str, Any], targets: list[str], build_passed: bool, source_hashes: dict[str, str]) -> dict[str, Any]:
    decisions = []
    evidence_nodes = []
    edges = []

    def node(nid, ntype, **extra):
        evidence_nodes.append({"id": nid, "type": ntype, **extra})

    component_nodes = set()
    for target in targets:
        for kind in KINDS:
            for component in projection["closures"][target][kind]:
                nid = f"component:{component}"
                if nid not in component_nodes:
                    node(nid, "external_component", component_id=component)
                    component_nodes.add(nid)

    for target in targets:
        build_receipt = f"receipt:{target}:build"
        node(build_receipt, "build_receipt", passed=bool(build_passed), source_hash=source_hashes[target])

        security_decision_ids = {}
        for kind in KINDS:
            receipt = f"receipt:{target}:{kind}_security"
            node(receipt, "security_receipt", dependency_kind=kind, target=target)
            dtype = SECURITY_DECISION_BY_KIND[kind]
            did = f"decision:{target}:{dtype}"
            node(did, "decision", target=target, decision_type=dtype)
            security_decision_ids[kind] = did
            for component in projection["closures"][target][kind]:
                edges.append({"from": f"component:{component}", "to": receipt, "edge_type": "component_support"})
            edges.append({"from": receipt, "to": did, "edge_type": "receipt_support"})
            decisions.append({
                "decision_id": did, "target": target, "decision_type": dtype,
                "standing": "ACCEPTED", "receipt_id": receipt,
            })

        build_did = f"decision:{target}:build_acceptance"
        node(build_did, "decision", target=target, decision_type="build_acceptance")
        edges.append({"from": build_receipt, "to": build_did, "edge_type": "receipt_support"})
        decisions.append({
            "decision_id": build_did, "target": target, "decision_type": "build_acceptance",
            "standing": "ACCEPTED", "receipt_id": build_receipt,
        })

        promo = f"decision:{target}:promotion_permission"
        node(promo, "decision", target=target, decision_type="promotion_permission")
        edges.append({"from": security_decision_ids["runtime"], "to": promo, "edge_type": "decision_support"})
        edges.append({"from": security_decision_ids["build"], "to": promo, "edge_type": "decision_support"})
        edges.append({"from": build_did, "to": promo, "edge_type": "decision_support"})
        decisions.append({
            "decision_id": promo, "target": target, "decision_type": "promotion_permission",
            "standing": "ACCEPTED", "receipt_id": None,
        })

    # deterministic receipt bindings
    receipts = []
    for target in targets:
        for kind in KINDS:
            body = {
                "schema": "openline.psd001.security-receipt.v1",
                "target": target,
                "dependency_kind": kind,
                "components": projection["closures"][target][kind],
                "result": "PASS",
                "policy_authority": "NONE",
            }
            receipts.append({**body, "receipt_sha256": digest_obj(body)})
        body = {
            "schema": "openline.psd001.build-receipt.v1",
            "target": target,
            "source_hash": source_hashes[target],
            "result": "PASS" if build_passed else "FAIL",
            "policy_authority": "NONE",
        }
        receipts.append({**body, "receipt_sha256": digest_obj(body)})

    model = {
        "schema": "openline.ace.psd001.t0-model.v1",
        "targets": targets,
        "decisions": sorted(decisions, key=lambda x: x["decision_id"]),
        "evidence_nodes": sorted(evidence_nodes, key=lambda x: x["id"]),
        "evidence_edges": sorted(edges, key=lambda x: (x["from"], x["to"], x["edge_type"])),
        "closures": projection["closures"],
        "union": projection["union"],
        "receipts": sorted(receipts, key=lambda x: (x["target"], x["schema"], x.get("dependency_kind", ""))),
        "build_passed": bool(build_passed),
        "source_hashes": source_hashes,
        "policy_authority": "NONE",
        "runtime_permission": "NONE",
    }
    model["model_sha256"] = digest_obj({k:v for k,v in model.items() if k != "model_sha256"})
    return model

def intervention_seed(experiment_id: str, upstream_commit: str, freeze_sha256: str) -> int:
    h = hashlib.sha256(f"{experiment_id}|{upstream_commit}|{freeze_sha256}".encode()).digest()
    return int.from_bytes(h[:8], "big")

def _ranked(items: list[str], seed: int, label: str) -> list[str]:
    def key(x):
        return hashlib.sha256(f"{seed}|{label}|{x}".encode()).hexdigest()
    return sorted(items, key=key)

def select_interventions(projection: dict[str, Any], targets: list[str], seed: int, counts: dict[str, int]) -> list[dict[str, Any]]:
    membership = defaultdict(set)
    for target in targets:
        for c in projection["union"][target]:
            membership[c].add(target)

    shared = [c for c, ts in membership.items() if len(ts) >= 2]
    single = [c for c, ts in membership.items() if len(ts) == 1]
    absent = list(projection["absent_components"])

    ns = counts["shared"]
    ni = counts["single"]
    na = counts["absent"]
    nm = counts["missing_edge"]
    if len(shared) < ns or len(single) < ni or len(absent) < na:
        raise PSD001Error(
            f"insufficient_intervention_pool:shared={len(shared)}/{ns}:single={len(single)}/{ni}:absent={len(absent)}/{na}"
        )

    trials = []
    selected_affected = []
    for label, pool, n in [
        ("shared", shared, ns),
        ("single", single, ni),
        ("absent", absent, na),
    ]:
        for idx, component in enumerate(_ranked(pool, seed, label)[:n]):
            tid = f"{label}-{idx+1:02d}"
            trial = {
                "trial_id": tid,
                "arm": "complete_graph",
                "stratum": label,
                "component_id": component,
                "graph_damage": None,
            }
            trials.append(trial)
            if label != "absent":
                selected_affected.append(trial)

    # Missing-edge pairs: choose affected trials deterministically, then choose one
    # actually affected target/kind edge from t0 closure membership.
    candidates = _ranked([t["trial_id"] for t in selected_affected], seed, "missing-pairs")
    by_id = {t["trial_id"]: t for t in selected_affected}
    for idx, base_id in enumerate(candidates[:nm]):
        base = by_id[base_id]
        component = base["component_id"]
        edge_candidates = []
        for target in targets:
            for kind in KINDS:
                if component in projection["closures"][target][kind]:
                    edge_candidates.append((target, kind))
        if not edge_candidates:
            raise PSD001Error(f"missing_edge_no_actual_edge:{component}")
        ranked_edges = sorted(
            edge_candidates,
            key=lambda tk: hashlib.sha256(f"{seed}|missing-edge|{base_id}|{tk[0]}|{tk[1]}".encode()).hexdigest()
        )
        target, kind = ranked_edges[0]
        trials.append({
            "trial_id": f"missing-{idx+1:02d}",
            "arm": "known_missing_edge",
            "stratum": base["stratum"],
            "component_id": component,
            "paired_complete_trial_id": base_id,
            "graph_damage": {"target": target, "kind": kind, "known_incomplete": True},
        })

    return sorted(trials, key=lambda x: x["trial_id"])

def oracle_ground_truth(t0: dict[str, Any], component: str) -> dict[str, bool]:
    # Independent decision semantics: no graph traversal.
    out = {}
    for d in t0["decisions"]:
        target, dtype = d["target"], d["decision_type"]
        runtime = component in t0["closures"][target]["runtime"]
        build = component in t0["closures"][target]["build"]
        dev = component in t0["closures"][target]["dev"]
        if dtype == "runtime_security_acceptance":
            affected = runtime
        elif dtype == "build_security_acceptance":
            affected = build
        elif dtype == "test_security_acceptance":
            affected = dev
        elif dtype == "build_acceptance":
            affected = False
        elif dtype == "promotion_permission":
            affected = runtime or build
        else:
            raise PSD001Error(f"unknown_decision_type:{dtype}")
        out[d["decision_id"]] = affected
    return out

def _descendants(edges: list[dict[str, Any]], starts: set[str]) -> set[str]:
    adj = defaultdict(list)
    for e in edges:
        adj[e["from"]].append(e["to"])
    seen = set(starts)
    q = deque(starts)
    while q:
        x = q.popleft()
        for y in adj.get(x, []):
            if y not in seen:
                seen.add(y)
                q.append(y)
    return seen

def openline_predict(t0: dict[str, Any], trial: dict[str, Any]) -> dict[str, str]:
    component = trial["component_id"]
    start = f"component:{component}"
    edges = list(t0["evidence_edges"])
    unknown_decisions = set()

    damage = trial.get("graph_damage")
    if damage:
        target, kind = damage["target"], damage["kind"]
        receipt = f"receipt:{target}:{kind}_security"
        # remove exactly the relevant component-support edge
        edges = [
            e for e in edges
            if not (e["from"] == start and e["to"] == receipt and e["edge_type"] == "component_support")
        ]
        security_did = f"decision:{target}:{SECURITY_DECISION_BY_KIND[kind]}"
        # known missing relationship makes the security decision unresolved;
        # promotion inherits unresolved only when that security decision supports it.
        unknown_decisions.add(security_did)
        if kind in ("runtime", "build"):
            unknown_decisions.add(f"decision:{target}:promotion_permission")

    reached = _descendants(edges, {start}) if start in {n["id"] for n in t0["evidence_nodes"]} else {start}
    decisions = {d["decision_id"] for d in t0["decisions"]}
    out = {}
    for did in decisions:
        if did in reached:
            out[did] = "REOPEN"
        elif did in unknown_decisions:
            out[did] = "UNDETERMINED"
        else:
            out[did] = "RETAIN"
    return out

def artifact_join_predict(t0: dict[str, Any], component: str) -> dict[str, str]:
    affected_targets = {t for t, comps in t0["union"].items() if component in comps}
    return {
        d["decision_id"]: ("REOPEN" if d["target"] in affected_targets else "RETAIN")
        for d in t0["decisions"]
    }

def repo_join_predict(t0: dict[str, Any], component: str) -> dict[str, str]:
    hit = any(component in comps for comps in t0["union"].values())
    return {d["decision_id"]: ("REOPEN" if hit else "RETAIN") for d in t0["decisions"]}

def closure_index_predict(t0: dict[str, Any], component: str) -> dict[str, str]:
    out = {}
    for d in t0["decisions"]:
        target, dtype = d["target"], d["decision_type"]
        if dtype == "runtime_security_acceptance":
            affected = component in t0["closures"][target]["runtime"]
        elif dtype == "build_security_acceptance":
            affected = component in t0["closures"][target]["build"]
        elif dtype == "test_security_acceptance":
            affected = component in t0["closures"][target]["dev"]
        elif dtype == "build_acceptance":
            affected = False
        elif dtype == "promotion_permission":
            affected = (
                component in t0["closures"][target]["runtime"]
                or component in t0["closures"][target]["build"]
            )
        else:
            raise PSD001Error(dtype)
        out[d["decision_id"]] = "REOPEN" if affected else "RETAIN"
    return out

def headline_predict(t0: dict[str, Any]) -> dict[str, str]:
    return {d["decision_id"]: "RETAIN" for d in t0["decisions"]}

def run_trial(t0: dict[str, Any], trial: dict[str, Any]) -> dict[str, Any]:
    component = trial["component_id"]
    truth = oracle_ground_truth(t0, component)
    preds = {
        "openline_evidence_graph": openline_predict(t0, trial),
        "artifact_component_join": artifact_join_predict(t0, component),
        "repo_scope_join": repo_join_predict(t0, component),
        "decision_closure_index": closure_index_predict(t0, component),
        "headline_only": headline_predict(t0),
    }
    return {
        "trial": trial,
        "ground_truth": truth,
        "predictions": preds,
    }

def confusion(traces: list[dict[str, Any]], strategy: str, include_missing: bool = False) -> dict[str, Any]:
    tp=fp=fn=tn=und=0
    per_trial = []
    for tr in traces:
        if tr["trial"]["arm"] == "known_missing_edge" and not include_missing:
            continue
        if tr["trial"]["arm"] != "known_missing_edge" and include_missing:
            continue
        ltp=lfp=lfn=ltn=lund=0
        for did, affected in tr["ground_truth"].items():
            pred = tr["predictions"][strategy][did]
            if pred == "UNDETERMINED":
                und += 1; lund += 1
                if affected:
                    fn += 1; lfn += 1
                continue
            reopened = pred == "REOPEN"
            if reopened and affected:
                tp += 1; ltp += 1
            elif reopened and not affected:
                fp += 1; lfp += 1
            elif (not reopened) and affected:
                fn += 1; lfn += 1
            else:
                tn += 1; ltn += 1
        per_trial.append({"trial_id": tr["trial"]["trial_id"], "tp":ltp,"fp":lfp,"fn":lfn,"tn":ltn,"undetermined":lund})
    recall = tp/(tp+fn) if tp+fn else 1.0
    precision = tp/(tp+fp) if tp+fp else 1.0
    fir = fp/(fp+tn) if fp+tn else 0.0
    spec = tn/(tn+fp) if tn+fp else 1.0
    return {
        "tp":tp,"fp":fp,"fn":fn,"tn":tn,"undetermined":und,
        "decision_recall":recall,"decision_precision":precision,
        "false_reopen_rate":fir,"retention_specificity":spec,
        "per_trial":per_trial,
    }

def missing_edge_safety(traces: list[dict[str, Any]]) -> dict[str, Any]:
    affected = silent_retain = unresolved = total = 0
    for tr in traces:
        if tr["trial"]["arm"] != "known_missing_edge":
            continue
        for did, truth in tr["ground_truth"].items():
            total += 1
            pred = tr["predictions"]["openline_evidence_graph"][did]
            if pred == "UNDETERMINED":
                unresolved += 1
            if truth:
                affected += 1
                if pred == "RETAIN":
                    silent_retain += 1
    return {
        "affected_decision_count": affected,
        "silent_false_retain_count": silent_retain,
        "silent_false_retain_rate": silent_retain/affected if affected else 0.0,
        "undetermined_count": unresolved,
        "unresolved_rate": unresolved/total if total else 0.0,
    }

def equivalence_mismatches(traces: list[dict[str, Any]]) -> int:
    n=0
    for tr in traces:
        if tr["trial"]["arm"] != "complete_graph":
            continue
        a=tr["predictions"]["openline_evidence_graph"]
        b=tr["predictions"]["decision_closure_index"]
        n += sum(a[k] != b[k] for k in a)
    return n

def bootstrap_false_reopen_difference(traces: list[dict[str, Any]], resamples: int, seed: int) -> dict[str, Any]:
    complete = [tr for tr in traces if tr["trial"]["arm"] == "complete_graph"]
    if not complete:
        raise PSD001Error("no_complete_trials")
    rng = random.Random(seed)
    diffs=[]
    for _ in range(resamples):
        sample=[complete[rng.randrange(len(complete))] for __ in range(len(complete))]
        olp=confusion(sample,"openline_evidence_graph",include_missing=False)
        art=confusion(sample,"artifact_component_join",include_missing=False)
        diffs.append(art["false_reopen_rate"]-olp["false_reopen_rate"])
    diffs.sort()
    lo=diffs[int(0.025*(resamples-1))]
    hi=diffs[int(0.975*(resamples-1))]
    olp=confusion(complete,"openline_evidence_graph")
    art=confusion(complete,"artifact_component_join")
    return {
        "observed_difference":art["false_reopen_rate"]-olp["false_reopen_rate"],
        "ci_lower":lo,"ci_upper":hi,"resamples":resamples,"seed":seed,
    }

def data_sufficiency(t0: dict[str, Any], trials: list[dict[str, Any]], pool: dict[str, int], prereg: dict[str, Any]) -> dict[str, Any]:
    c=prereg["data_sufficiency"]
    complete=sum(t["arm"]=="complete_graph" for t in trials)
    missing=sum(t["arm"]=="known_missing_edge" for t in trials)
    checks={
        "exact_targets":len(t0["targets"])==c["exact_target_count"],
        "exact_decisions":len(t0["decisions"])==c["exact_t0_decisions"],
        "build_passed":t0["build_passed"] is c["all_target_build_checks_pass"],
        "shared_pool":pool["shared"]>=c["minimum_shared_components"],
        "single_pool":pool["single"]>=c["minimum_single_target_components"],
        "absent_pool":pool["absent"]>=c["minimum_absent_components"],
        "complete_trials":complete>=c["minimum_complete_trials"],
        "missing_trials":missing>=c["minimum_missing_edge_trials"],
    }
    return {"sufficient":all(checks.values()),"checks":checks,"complete_trials":complete,"missing_edge_trials":missing,"pool":pool}

def adjudicate(t0: dict[str, Any], traces: list[dict[str, Any]], pool: dict[str, int], prereg: dict[str, Any]) -> dict[str, Any]:
    suff=data_sufficiency(t0,[tr["trial"] for tr in traces],pool,prereg)
    if not suff["sufficient"]:
        return {"verdict":"DATA_INSUFFICIENT","data_sufficiency":suff}

    metrics={s:confusion(traces,s) for s in PRIMARY_STRATEGIES}
    safety=missing_edge_safety(traces)
    eq=equivalence_mismatches(traces)

    if safety["silent_false_retain_rate"] > prereg["positive_criteria"]["missing_edge_silent_false_retain_rate"]:
        return {
            "verdict":"SAFETY_FAILURE","data_sufficiency":suff,"metrics":metrics,
            "missing_edge_safety":safety,"equivalence_mismatches":eq
        }

    olp=metrics["openline_evidence_graph"]
    art=metrics["artifact_component_join"]
    base_fir=art["false_reopen_rate"]
    reduction=0.0 if base_fir<=0 else 1.0-olp["false_reopen_rate"]/base_fir
    boot=bootstrap_false_reopen_difference(
        traces,prereg["bootstrap"]["resamples"],prereg["bootstrap"]["seed"]
    )
    pc=prereg["positive_criteria"]
    criteria={
        "openline_recall":olp["decision_recall"]>=pc["openline_min_recall"],
        "openline_precision":olp["decision_precision"]>=pc["openline_min_precision"],
        "artifact_recall_fair":art["decision_recall"]>=pc["artifact_join_min_recall_for_fair_comparison"],
        "false_reopen_reduction":reduction>=pc["minimum_false_reopen_reduction_vs_artifact_join"],
        "not_artifact_precision_parity":art["decision_precision"] < pc["artifact_precision_parity_ratio"]*olp["decision_precision"],
        "bootstrap_ci_positive":boot["ci_lower"]>0.0 if pc["bootstrap_false_reopen_difference_ci_lower_gt_zero"] else True,
        "equivalent_index_matches":eq==pc["complete_graph_equivalence_index_mismatches"],
        "missing_edge_safe":safety["silent_false_retain_rate"]==pc["missing_edge_silent_false_retain_rate"],
    }
    verdict="SELECTIVE_LOCALIZATION_ADVANTAGE" if all(criteria.values()) else "CAPABILITY_PARITY"
    return {
        "verdict":verdict,"data_sufficiency":suff,"metrics":metrics,
        "selective_blast_radius_reduction":reduction,
        "bootstrap_false_reopen_difference":boot,
        "missing_edge_safety":safety,
        "equivalence_mismatches":eq,
        "criteria":criteria,
    }
