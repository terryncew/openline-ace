from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean
from typing import Any, Mapping, Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


class SelectorError(ValueError):
    pass


@dataclass(frozen=True)
class Threshold:
    operator: str
    value: float


def is_liability(value: float, threshold: Threshold) -> bool:
    if threshold.operator == "<=":
        return float(value) > threshold.value
    if threshold.operator == ">=":
        return float(value) < threshold.value
    raise SelectorError(f"unsupported_threshold_operator:{threshold.operator}")


def build_matrices(candidates, assay_order, thresholds):
    values, flags = {}, {}
    for candidate in candidates:
        cid = str(candidate["candidate_id"])
        if cid in values:
            raise SelectorError(f"duplicate_candidate:{cid}")
        values[cid], flags[cid] = {}, {}
        for assay in assay_order:
            v = candidate["assays"].get(assay)
            if v is None or not math.isfinite(float(v)):
                raise SelectorError(f"missing_assay:{cid}:{assay}")
            values[cid][assay] = float(v)
            flags[cid][assay] = is_liability(float(v), thresholds[assay])
    return values, flags


def _training_ids(candidate_ids, holdout):
    return [cid for cid in candidate_ids if cid != holdout]


def _prevalence(flags, train_ids, assay):
    return sum(bool(flags[cid][assay]) for cid in train_ids) / len(train_ids)


def fixed_prevalence_order(flags, train_ids, assay_order):
    rank = {a: i for i, a in enumerate(assay_order)}
    return sorted(assay_order, key=lambda a: (-_prevalence(flags, train_ids, a), rank[a]))


def greedy_coverage_order(flags, train_ids, assay_order):
    rank = {a: i for i, a in enumerate(assay_order)}
    remaining = set(assay_order)
    covered = set()
    order = []
    while remaining:
        assay = sorted(
            remaining,
            key=lambda a: (
                -sum(bool(flags[cid][a]) and cid not in covered for cid in train_ids),
                rank[a],
            ),
        )[0]
        order.append(assay)
        remaining.remove(assay)
        covered.update(cid for cid in train_ids if flags[cid][assay])
    return order


def predict_remaining_risks(*, train_ids, holdout, observed, remaining, values, flags, binary_features):
    if not observed:
        return {assay: _prevalence(flags, train_ids, assay) for assay in remaining}
    if binary_features:
        x_train = np.asarray([[float(flags[cid][f]) for f in observed] for cid in train_ids], dtype=float)
        x_holdout = np.asarray([[float(flags[holdout][f]) for f in observed]], dtype=float)
    else:
        x_train = np.asarray([[float(values[cid][f]) for f in observed] for cid in train_ids], dtype=float)
        x_holdout = np.asarray([[float(values[holdout][f]) for f in observed]], dtype=float)
    risks = {}
    for assay in remaining:
        y = np.asarray([int(flags[cid][assay]) for cid in train_ids], dtype=int)
        if len(set(int(v) for v in y.tolist())) < 2:
            risks[assay] = float(y[0])
            continue
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(
                penalty="l2", C=1.0, solver="liblinear", fit_intercept=True,
                class_weight=None, max_iter=1000, random_state=0,
            ),
        )
        model.fit(x_train, y)
        risks[assay] = float(model.predict_proba(x_holdout)[0, 1])
    return risks


def bernoulli_entropy(p):
    p = min(1.0, max(0.0, float(p)))
    if p in (0.0, 1.0):
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def dynamic_trace(*, candidate_ids, holdout, assay_order, values, flags, mode):
    if mode not in {"continuous", "binary", "entropy"}:
        raise SelectorError(f"unsupported_dynamic_mode:{mode}")
    train_ids = _training_ids(candidate_ids, holdout)
    observed = []
    remaining = list(assay_order)
    rank = {a: i for i, a in enumerate(assay_order)}
    steps = []
    while remaining:
        risks = predict_remaining_risks(
            train_ids=train_ids, holdout=holdout, observed=observed,
            remaining=remaining, values=values, flags=flags,
            binary_features=(mode == "binary"),
        )
        if mode == "entropy":
            scores = {a: bernoulli_entropy(risks[a]) for a in remaining}
            assay = sorted(remaining, key=lambda a: (-scores[a], rank[a]))[0]
        else:
            scores = risks
            assay = sorted(remaining, key=lambda a: (-risks[a], rank[a]))[0]
        step = {
            "step": len(steps) + 1,
            "assay": assay,
            "predicted_liability_probability": risks[assay],
            "selection_score": scores[assay],
            "observed_value": values[holdout][assay],
            "liability": bool(flags[holdout][assay]),
        }
        steps.append(step)
        remaining.remove(assay)
        if flags[holdout][assay]:
            break
        observed.append(assay)
    return {
        "candidate_id": holdout,
        "has_any_liability": any(flags[holdout].values()),
        "assays_spent": len(steps),
        "steps": steps,
    }


def fixed_trace(order, holdout, values, flags):
    steps = []
    for assay in order:
        steps.append({
            "step": len(steps) + 1,
            "assay": assay,
            "observed_value": values[holdout][assay],
            "liability": bool(flags[holdout][assay]),
        })
        if flags[holdout][assay]:
            break
    return {
        "candidate_id": holdout,
        "has_any_liability": any(flags[holdout].values()),
        "assays_spent": len(steps),
        "steps": steps,
    }


def summarize_traces(traces, budgets=(1, 2, 3, 4, 5)):
    positive = [t for t in traces if t["has_any_liability"]]
    if not positive:
        raise SelectorError("no_liability_positive_candidates")
    out = {
        "candidate_count": len(traces),
        "liability_positive_count": len(positive),
        "liability_negative_count": len(traces) - len(positive),
        "mean_assays_to_first_liability_positive_only": mean(float(t["assays_spent"]) for t in positive),
        "budgets": {},
    }
    for budget in budgets:
        detected = sum(int(t["has_any_liability"] and int(t["assays_spent"]) <= budget) for t in traces)
        survivors = [t for t in traces if int(t["assays_spent"]) > budget]
        hidden = sum(int(t["has_any_liability"]) for t in survivors)
        out["budgets"][str(budget)] = {
            "positive_detected_count": detected,
            "positive_detected_fraction": detected / len(positive),
            "survivor_count": len(survivors),
            "hidden_liability_count": hidden,
            "false_reassurance_fraction": hidden / len(survivors) if survivors else 0.0,
        }
    return out


def random_expected_summary(flags, candidate_ids, assay_order, budgets=(1, 2, 3, 4, 5)):
    n = len(assay_order)
    positive = [cid for cid in candidate_ids if any(flags[cid].values())]
    if not positive:
        raise SelectorError("no_liability_positive_candidates")
    costs = {}
    for cid in positive:
        k = sum(bool(flags[cid][a]) for a in assay_order)
        costs[cid] = (n + 1) / (k + 1)
    out = {
        "candidate_count": len(candidate_ids),
        "liability_positive_count": len(positive),
        "liability_negative_count": len(candidate_ids) - len(positive),
        "mean_assays_to_first_liability_positive_only": mean(costs.values()),
        "budgets": {},
        "method": "analytic uniform random permutation expectation",
    }
    negatives = len(candidate_ids) - len(positive)
    for budget in budgets:
        pos_survivors = 0.0
        for cid in positive:
            k = sum(bool(flags[cid][a]) for a in assay_order)
            survive = 0.0 if budget > n - k else math.comb(n - k, budget) / math.comb(n, budget)
            pos_survivors += survive
        detected = len(positive) - pos_survivors
        survivors = negatives + pos_survivors
        out["budgets"][str(budget)] = {
            "positive_detected_count": detected,
            "positive_detected_fraction": detected / len(positive),
            "survivor_count": survivors,
            "hidden_liability_count": pos_survivors,
            "false_reassurance_fraction": pos_survivors / survivors if survivors else 0.0,
        }
    return out, costs


def run_leave_one_out(candidates, assay_order, thresholds, budgets=(1, 2, 3, 4, 5)):
    values, flags = build_matrices(candidates, assay_order, thresholds)
    candidate_ids = sorted(values)
    traces = {name: [] for name in (
        "fixed_prevalence", "greedy_fixed_coverage", "binary_dynamic",
        "continuous_value_conditional_risk", "entropy_information_gain",
    )}
    for holdout in candidate_ids:
        train_ids = _training_ids(candidate_ids, holdout)
        traces["fixed_prevalence"].append(fixed_trace(fixed_prevalence_order(flags, train_ids, assay_order), holdout, values, flags))
        traces["greedy_fixed_coverage"].append(fixed_trace(greedy_coverage_order(flags, train_ids, assay_order), holdout, values, flags))
        traces["binary_dynamic"].append(dynamic_trace(candidate_ids=candidate_ids, holdout=holdout, assay_order=assay_order, values=values, flags=flags, mode="binary"))
        traces["continuous_value_conditional_risk"].append(dynamic_trace(candidate_ids=candidate_ids, holdout=holdout, assay_order=assay_order, values=values, flags=flags, mode="continuous"))
        traces["entropy_information_gain"].append(dynamic_trace(candidate_ids=candidate_ids, holdout=holdout, assay_order=assay_order, values=values, flags=flags, mode="entropy"))
    metrics = {name: summarize_traces(items, budgets) for name, items in traces.items()}
    random_metrics, random_costs = random_expected_summary(flags, candidate_ids, assay_order, budgets)
    metrics["uniform_random_expected"] = random_metrics
    costs = {}
    for name, items in traces.items():
        costs[name] = {t["candidate_id"]: float(t["assays_spent"]) for t in items if t["has_any_liability"]}
    costs["uniform_random_expected"] = random_costs
    return {
        "candidate_ids": candidate_ids,
        "liability_flags": flags,
        "traces": traces,
        "metrics": metrics,
        "positive_candidate_costs": costs,
    }


def strongest_comparator(metrics, comparator_names, budget=3):
    return sorted(
        comparator_names,
        key=lambda name: (
            float(metrics[name]["mean_assays_to_first_liability_positive_only"]),
            float(metrics[name]["budgets"][str(budget)]["false_reassurance_fraction"]),
            name,
        ),
    )[0]


def paired_bootstrap_ci(target_costs, comparator_costs, candidate_ids, resamples=10000, seed=0):
    ids = list(candidate_ids)
    if not ids:
        raise SelectorError("empty_bootstrap_cohort")
    diffs = np.asarray([float(target_costs[cid]) - float(comparator_costs[cid]) for cid in ids], dtype=float)
    rng = np.random.default_rng(seed)
    boot = np.empty(resamples, dtype=float)
    n = len(diffs)
    for i in range(resamples):
        idx = rng.integers(0, n, size=n)
        boot[i] = float(np.mean(diffs[idx]))
    return {
        "paired_candidate_count": n,
        "observed_mean_difference": float(np.mean(diffs)),
        "ci_lower": float(np.quantile(boot, 0.025)),
        "ci_upper": float(np.quantile(boot, 0.975)),
        "resamples": int(resamples),
        "seed": int(seed),
    }


def adjudicate(run, prereg):
    target = prereg["target_strategy"]
    comparator = strongest_comparator(run["metrics"], prereg["comparators"], int(prereg["primary_budget"]))
    positive_ids = sorted(run["positive_candidate_costs"][target])
    boot = paired_bootstrap_ci(
        run["positive_candidate_costs"][target],
        run["positive_candidate_costs"][comparator],
        positive_ids,
        int(prereg["bootstrap"]["resamples"]),
        int(prereg["bootstrap"]["seed"]),
    )
    target_metric = run["metrics"][target]
    comp_metric = run["metrics"][comparator]
    b = str(prereg["primary_budget"])
    target_cost = float(target_metric["mean_assays_to_first_liability_positive_only"])
    comp_cost = float(comp_metric["mean_assays_to_first_liability_positive_only"])
    target_fr = float(target_metric["budgets"][b]["false_reassurance_fraction"])
    comp_fr = float(comp_metric["budgets"][b]["false_reassurance_fraction"])
    win = target_cost < comp_cost and boot["ci_upper"] < 0.0 and target_fr <= comp_fr
    return {
        "verdict": "EXTERNAL_ALLOCATION_ADVANTAGE_SUPPORTED" if win else "EXTERNAL_GENERALIZATION_NOT_SUPPORTED",
        "target_strategy": target,
        "strongest_comparator": comparator,
        "target_mean_cost": target_cost,
        "comparator_mean_cost": comp_cost,
        "target_false_reassurance_budget_3": target_fr,
        "comparator_false_reassurance_budget_3": comp_fr,
        "paired_bootstrap": boot,
        "criteria": {
            "strictly_lower_mean_cost": target_cost < comp_cost,
            "bootstrap_ci_upper_below_zero": boot["ci_upper"] < 0.0,
            "false_reassurance_no_worse": target_fr <= comp_fr,
        },
    }
