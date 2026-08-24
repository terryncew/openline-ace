from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import math
import random
from statistics import median
from typing import Any, Iterable


NEGATIVE_CATEGORIES = (
    "out_of_path_colocation",
    "post_fix_decision",
    "non_invalidating_upstream_mutation",
    "dead_or_dev_dependency",
    "sibling_valid_decision",
)

PRIMARY_FLATS = ("artifact_component_join", "repo_scope_flat_join")


class SLD004Error(ValueError):
    pass


def parse_time(value: str) -> datetime:
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise SLD004Error(f"timestamp_requires_timezone:{value}")
    return dt.astimezone(timezone.utc)


def _source_complete(source: dict[str, Any]) -> bool:
    required = ("locator", "published_at", "captured_sha256", "assertion")
    if not all(source.get(k) for k in required):
        return False
    digest = str(source["captured_sha256"])
    return len(digest) == 64 and all(c in "0123456789abcdef" for c in digest.lower())


def validate_case(case: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    cid = str(case.get("case_id", ""))
    if not cid:
        errors.append("missing_case_id")

    signal = case.get("signal") or {}
    try:
        t1 = parse_time(signal.get("t1", ""))
    except Exception:
        t1 = None
        errors.append("invalid_signal_t1")

    if not signal.get("affected_component_ids"):
        errors.append("missing_affected_component_ids")
    if not signal.get("invalidated_evidence_node_ids"):
        errors.append("missing_invalidated_evidence_node_ids")
    if not _source_complete(signal.get("source") or {}):
        errors.append("incomplete_signal_source")

    nodes = {str(n.get("id")): n for n in case.get("evidence_nodes", []) if n.get("id")}
    edges = case.get("evidence_edges", [])
    if not nodes:
        errors.append("missing_evidence_nodes")
    if not edges:
        errors.append("missing_evidence_edges")

    adjacency: dict[str, list[str]] = defaultdict(list)
    indegree: dict[str, int] = defaultdict(int)
    for idx, edge in enumerate(edges):
        a, b = str(edge.get("from", "")), str(edge.get("to", ""))
        if a not in nodes or b not in nodes:
            errors.append(f"edge_endpoint_missing:{idx}")
            continue
        adjacency[a].append(b)
        indegree[b] += 1
        indegree.setdefault(a, indegree.get(a, 0))
        src = edge.get("source") or {}
        if not _source_complete(src):
            errors.append(f"incomplete_edge_source:{idx}")
        elif t1 is not None:
            try:
                if parse_time(src["published_at"]) > t1:
                    errors.append(f"future_leakage_edge_source:{idx}")
            except Exception:
                errors.append(f"invalid_edge_source_time:{idx}")

    # DAG check independent of scientific outcome.
    if nodes:
        q = deque([n for n in nodes if indegree.get(n, 0) == 0])
        visited = 0
        indeg = dict(indegree)
        while q:
            n = q.popleft()
            visited += 1
            for nxt in adjacency.get(n, []):
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    q.append(nxt)
        if visited != len(nodes):
            errors.append("evidence_graph_not_dag")

    decisions = case.get("decisions", [])
    if len(decisions) < 2:
        errors.append("need_at_least_two_decisions")
    truth = []
    for i, d in enumerate(decisions):
        did = str(d.get("decision_id", ""))
        if not did:
            errors.append(f"missing_decision_id:{i}")
        if d.get("decision_node_id") not in nodes:
            errors.append(f"decision_node_missing:{did or i}")
        if not d.get("artifact_id"):
            errors.append(f"missing_immutable_artifact_id:{did or i}")
        if not isinstance(d.get("artifact_components"), list):
            errors.append(f"missing_artifact_components:{did or i}")
        for label in ("decision_source", "artifact_source"):
            src = d.get(label) or {}
            if not _source_complete(src):
                errors.append(f"incomplete_{label}:{did or i}")
            elif t1 is not None:
                try:
                    if parse_time(src["published_at"]) > t1:
                        errors.append(f"future_leakage_{label}:{did or i}")
                except Exception:
                    errors.append(f"invalid_{label}_time:{did or i}")
        try:
            accepted = parse_time(d.get("accepted_at", ""))
            if t1 is not None and accepted >= t1:
                errors.append(f"decision_not_pre_signal:{did or i}")
        except Exception:
            errors.append(f"invalid_accepted_at:{did or i}")

        gt = d.get("ground_truth") or {}
        if gt.get("affected") not in (True, False):
            errors.append(f"missing_ground_truth_label:{did or i}")
        else:
            truth.append(bool(gt["affected"]))
        if not _source_complete(gt.get("source") or {}):
            errors.append(f"incomplete_ground_truth_source:{did or i}")
        try:
            t3 = parse_time(gt.get("t3", ""))
            if t1 is not None and t3 <= t1:
                errors.append(f"t3_not_after_t1:{did or i}")
        except Exception:
            errors.append(f"invalid_t3:{did or i}")
        cat = d.get("negative_control_category")
        if cat is not None and cat not in NEGATIVE_CATEGORIES:
            errors.append(f"unknown_negative_control_category:{did or i}:{cat}")

    if decisions and truth:
        if not any(truth):
            errors.append("case_has_no_affected_decision")
        if all(truth):
            errors.append("case_has_no_unaffected_decision")

    invalid_nodes = set(map(str, signal.get("invalidated_evidence_node_ids") or []))
    for n in invalid_nodes:
        if n not in nodes:
            errors.append(f"invalidated_node_missing:{n}")

    return {
        "case_id": cid,
        "admissible": not errors,
        "errors": sorted(set(errors)),
        "decision_count": len(decisions),
    }


def reachable_decisions(case: dict[str, Any]) -> set[str]:
    nodes = {str(n["id"]): n for n in case["evidence_nodes"]}
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in case["evidence_edges"]:
        adjacency[str(edge["from"])].append(str(edge["to"]))
    starts = list(map(str, case["signal"]["invalidated_evidence_node_ids"]))
    q = deque(starts)
    seen = set(starts)
    decision_nodes = {str(d["decision_node_id"]): str(d["decision_id"]) for d in case["decisions"]}
    out: set[str] = set()
    while q:
        n = q.popleft()
        if n in decision_nodes:
            out.add(decision_nodes[n])
        for nxt in adjacency.get(n, []):
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    return out


def predictions(case: dict[str, Any], ttl_days: int = 30) -> dict[str, set[str]]:
    t1 = parse_time(case["signal"]["t1"])
    affected_components = set(map(str, case["signal"]["affected_component_ids"]))
    active = [d for d in case["decisions"] if d.get("active_at_t1", True)]
    active_ids = {str(d["decision_id"]) for d in active}

    artifact = {
        str(d["decision_id"]) for d in active
        if affected_components.intersection(set(map(str, d.get("artifact_components", []))))
    }
    scopes_hit = {
        str(d.get("repo_scope", "")) for d in active
        if str(d["decision_id"]) in artifact
    }
    repo = {
        str(d["decision_id"]) for d in active
        if str(d.get("repo_scope", "")) in scopes_hit
    }
    ttl = {
        str(d["decision_id"]) for d in active
        if (t1 - parse_time(d["accepted_at"])).total_seconds() >= ttl_days * 86400
    }
    return {
        "openline_evidence_dag": reachable_decisions(case).intersection(active_ids),
        "artifact_component_join": artifact,
        "repo_scope_flat_join": repo,
        "any_change": set(active_ids),
        "ttl_freshness": ttl,
        "headline_only": set(),
    }


def confusion(cases: Iterable[dict[str, Any]], strategy: str) -> dict[str, Any]:
    tp = fp = fn = tn = 0
    by_category: dict[str, dict[str, int]] = {c: {"fp": 0, "tn": 0, "count": 0} for c in NEGATIVE_CATEGORIES}
    for case in cases:
        pred = predictions(case)[strategy]
        for d in case["decisions"]:
            if not d.get("active_at_t1", True):
                continue
            did = str(d["decision_id"])
            affected = bool(d["ground_truth"]["affected"])
            reopened = did in pred
            if reopened and affected:
                tp += 1
            elif reopened and not affected:
                fp += 1
            elif (not reopened) and affected:
                fn += 1
            else:
                tn += 1
            cat = d.get("negative_control_category")
            if cat in by_category and not affected:
                by_category[cat]["count"] += 1
                if reopened:
                    by_category[cat]["fp"] += 1
                else:
                    by_category[cat]["tn"] += 1

    recall = tp / (tp + fn) if tp + fn else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    fir = fp / (fp + tn) if fp + tn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "decision_recall": recall,
        "decision_precision": precision,
        "false_reopen_rate": fir,
        "retention_specificity": specificity,
        "negative_controls": by_category,
    }


def opportunity_windows(cases: Iterable[dict[str, Any]]) -> list[float]:
    out = []
    for case in cases:
        t1 = parse_time(case["signal"]["t1"])
        for d in case["decisions"]:
            if d.get("active_at_t1", True) and bool(d["ground_truth"]["affected"]):
                t3 = parse_time(d["ground_truth"]["t3"])
                out.append((t3 - t1).total_seconds() / 3600.0)
    return out


def data_sufficiency(cases: list[dict[str, Any]], prereg: dict[str, Any]) -> dict[str, Any]:
    cfg = prereg["f1_data_sufficiency"]
    validations = [validate_case(c) for c in cases]
    decision_count = sum(v["decision_count"] for v in validations)
    affected = sum(
        int(bool(d["ground_truth"]["affected"]))
        for c in cases for d in c.get("decisions", []) if d.get("active_at_t1", True)
    )
    unaffected = sum(
        int(not bool(d["ground_truth"]["affected"]))
        for c in cases for d in c.get("decisions", []) if d.get("active_at_t1", True)
    )
    neg = [
        d for c in cases for d in c.get("decisions", [])
        if d.get("active_at_t1", True)
        and not bool(d["ground_truth"]["affected"])
        and d.get("negative_control_category") in NEGATIVE_CATEGORIES
    ]
    cats = {d.get("negative_control_category") for d in neg}
    checks = {
        "minimum_cases": len(cases) >= cfg["minimum_cases"],
        "all_cases_admissible": all(v["admissible"] for v in validations),
        "minimum_decisions": decision_count >= cfg["minimum_decisions"],
        "minimum_affected": affected >= cfg["minimum_affected_decisions"],
        "minimum_unaffected": unaffected >= cfg["minimum_unaffected_decisions"],
        "minimum_negative_controls": len(neg) >= cfg["minimum_negative_controls"],
        "negative_to_affected_ratio": (len(neg) / affected if affected else 0.0) >= cfg["minimum_negative_to_affected_ratio"],
        "all_negative_categories": set(NEGATIVE_CATEGORIES).issubset(cats),
    }
    return {
        "sufficient": all(checks.values()),
        "checks": checks,
        "case_validations": validations,
        "case_count": len(cases),
        "decision_count": decision_count,
        "affected_count": affected,
        "unaffected_count": unaffected,
        "negative_control_count": len(neg),
        "negative_categories_present": sorted(c for c in cats if c),
    }


def select_primary_flat(metrics: dict[str, dict[str, Any]]) -> str | None:
    eligible = [
        name for name in PRIMARY_FLATS
        if float(metrics[name]["decision_recall"]) >= 0.95
    ]
    if not eligible:
        return None
    return sorted(
        eligible,
        key=lambda name: (
            -float(metrics[name]["decision_precision"]),
            float(metrics[name]["false_reopen_rate"]),
            name,
        ),
    )[0]


def _aggregate_sample(sample: list[dict[str, Any]], strategy: str) -> dict[str, Any]:
    return confusion(sample, strategy)


def bootstrap_precision_difference(
    cases: list[dict[str, Any]],
    flat: str,
    resamples: int = 10000,
    seed: int = 0,
) -> dict[str, float | int]:
    if not cases:
        raise SLD004Error("empty_bootstrap_cases")
    rng = random.Random(seed)
    diffs = []
    n = len(cases)
    for _ in range(resamples):
        sample = [cases[rng.randrange(n)] for __ in range(n)]
        a = _aggregate_sample(sample, "openline_evidence_dag")
        b = _aggregate_sample(sample, flat)
        diffs.append(float(a["decision_precision"]) - float(b["decision_precision"]))
    diffs.sort()
    lo = diffs[int(0.025 * (resamples - 1))]
    hi = diffs[int(0.975 * (resamples - 1))]
    observed = (
        confusion(cases, "openline_evidence_dag")["decision_precision"]
        - confusion(cases, flat)["decision_precision"]
    )
    return {
        "observed_difference": observed,
        "ci_lower": lo,
        "ci_upper": hi,
        "resamples": resamples,
        "seed": seed,
    }


def adjudicate(cases: list[dict[str, Any]], prereg: dict[str, Any]) -> dict[str, Any]:
    suff = data_sufficiency(cases, prereg)
    if not suff["sufficient"]:
        return {
            "verdict": "DATA_INSUFFICIENT",
            "data_sufficiency": suff,
            "policy_authority": "NONE",
            "runtime_permission": "NONE",
        }

    names = (
        "openline_evidence_dag", "artifact_component_join", "repo_scope_flat_join",
        "any_change", "ttl_freshness", "headline_only",
    )
    metrics = {name: confusion(cases, name) for name in names}
    flat = select_primary_flat(metrics)
    if flat is None:
        return {
            "verdict": "DATA_INSUFFICIENT",
            "reason": "no_flat_baseline_reaches_recall_0.95",
            "data_sufficiency": suff,
            "metrics": metrics,
            "policy_authority": "NONE",
            "runtime_permission": "NONE",
        }

    olp = metrics["openline_evidence_dag"]
    base = metrics[flat]
    base_fir = float(base["false_reopen_rate"])
    reduction = 0.0 if base_fir <= 0 else 1.0 - float(olp["false_reopen_rate"]) / base_fir
    boot = bootstrap_precision_difference(
        cases, flat,
        int(prereg["bootstrap"]["resamples"]),
        int(prereg["bootstrap"]["seed"]),
    )
    windows = opportunity_windows(cases)
    med_window = median(windows) if windows else 0.0
    t = prereg["f1_success_thresholds"]
    criteria = {
        "openline_recall": float(olp["decision_recall"]) >= t["openline_min_recall"],
        "openline_precision": float(olp["decision_precision"]) >= t["openline_min_precision"],
        "false_reopen_reduction": reduction >= t["minimum_false_reopen_rate_reduction_vs_primary_flat"],
        "not_precision_parity": float(base["decision_precision"]) < t["primary_flat_precision_parity_ratio"] * float(olp["decision_precision"]),
        "bootstrap_precision_ci": (boot["ci_lower"] > 0.0) if t["require_bootstrap_precision_difference_ci_lower_gt_zero"] else True,
        "positive_opportunity_window": med_window > 0.0 if t["require_positive_median_opportunity_window"] else True,
    }
    win = all(criteria.values())
    return {
        "verdict": "SELECTIVE_STANDING_PROPAGATION_ADVANTAGE" if win else "NO_SELECTIVE_STANDING_PROPAGATION_ADVANTAGE",
        "data_sufficiency": suff,
        "metrics": metrics,
        "selected_primary_flat_comparator": flat,
        "selective_blast_radius_reduction": reduction,
        "bootstrap_precision_difference": boot,
        "available_opportunity_window_hours": {
            "median": med_window,
            "values": windows,
            "operational_latency_claim": "NOT_ESTABLISHED",
        },
        "criteria": criteria,
        "policy_authority": "NONE",
        "runtime_permission": "NONE",
    }
