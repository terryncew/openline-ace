#!/usr/bin/env python3
import argparse
import json
from collections import defaultdict
from pathlib import Path

ACTION = {
    "no_action": 0,
    "monitor": 1,
    "formal_review": 2,
    "temporary_restriction": 3,
    "sanction": 4,
}
REQUIRED_ARMS = {
    "control",
    "matched_nuisance",
    "accusation_refuted",
    "accusation_refuted_evidence_first",
    "explicit_revocation",
    "calm_defense",
    "angry_defense",
}
NON_EVIDENTIARY = {"A", "[A]", "N", "[N]", "D", "[D]"}


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            row["_lineno"] = lineno
            rows.append(row)
    return rows


def validate(row):
    required = {"case_id", "receiver", "arm", "replicate", "wrongdoing_probability", "standing", "recommended_action", "basis_ids"}
    missing = required - row.keys()
    if missing:
        raise ValueError(f"line {row.get('_lineno')}: missing {sorted(missing)}")
    if row["arm"] not in REQUIRED_ARMS:
        raise ValueError(f"line {row['_lineno']}: invalid arm {row['arm']}")
    if not isinstance(row["replicate"], int) or row["replicate"] < 1:
        raise ValueError(f"line {row['_lineno']}: replicate must be a positive integer")
    for field in ("wrongdoing_probability", "standing"):
        if isinstance(row[field], bool) or not isinstance(row[field], (int, float)) or not 0 <= row[field] <= 100:
            raise ValueError(f"line {row['_lineno']}: {field} must be 0..100")
    if row["recommended_action"] not in ACTION:
        raise ValueError(f"line {row['_lineno']}: invalid recommended_action")
    if not isinstance(row["basis_ids"], list) or not all(isinstance(x, str) for x in row["basis_ids"]):
        raise ValueError(f"line {row['_lineno']}: basis_ids must be a list of strings")


def mean(xs):
    return sum(xs) / len(xs)


def _validate_design(rows):
    seen = set()
    grouped_reps = defaultdict(set)
    cases_by_receiver = defaultdict(set)
    for row in rows:
        validate(row)
        key = (row["receiver"], row["case_id"], row["arm"], row["replicate"])
        if key in seen:
            raise ValueError(f"duplicate result key: {key}")
        seen.add(key)
        grouped_reps[(row["receiver"], row["case_id"], row["arm"])].add(row["replicate"])
        cases_by_receiver[row["receiver"]].add(row["case_id"])

    for receiver, cases in cases_by_receiver.items():
        for case_id in cases:
            missing = [a for a in REQUIRED_ARMS if (receiver, case_id, a) not in grouped_reps]
            if missing:
                raise ValueError(f"incomplete design for {receiver}/{case_id}: missing arms {sorted(missing)}")
            rep_sets = {a: grouped_reps[(receiver, case_id, a)] for a in REQUIRED_ARMS}
            canonical = next(iter(rep_sets.values()))
            mismatched = {a: sorted(v) for a, v in rep_sets.items() if v != canonical}
            if mismatched:
                raise ValueError(f"replicate mismatch for {receiver}/{case_id}: {mismatched}; expected {sorted(canonical)}")


def summarize(rows):
    if not rows:
        raise ValueError("no results")
    _validate_design(rows)

    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["receiver"], row["case_id"], row["arm"])].append(row)

    receivers = sorted({r["receiver"] for r in rows})
    report = {"receivers": {}, "cross_receiver": {}}
    receiver_effects = {}

    for receiver in receivers:
        cases = sorted({r["case_id"] for r in rows if r["receiver"] == receiver})
        deltas = defaultdict(list)
        contamination = defaultdict(list)

        for case_id in cases:
            agg = {}
            for arm in REQUIRED_ARMS:
                vals = grouped[(receiver, case_id, arm)]
                agg[arm] = {
                    "risk": mean([v["wrongdoing_probability"] for v in vals]),
                    "standing": mean([v["standing"] for v in vals]),
                    "action": mean([ACTION[v["recommended_action"]] for v in vals]),
                }
                for v in vals:
                    basis = set(v["basis_ids"])
                    contamination[arm].append(1 if basis & NON_EVIDENTIARY else 0)

            deltas["accusation_debt_risk"].append(agg["accusation_refuted"]["risk"] - agg["control"]["risk"])
            deltas["accusation_debt_standing"].append(agg["control"]["standing"] - agg["accusation_refuted"]["standing"])
            deltas["accusation_action_escalation"].append(agg["accusation_refuted"]["action"] - agg["control"]["action"])
            deltas["accusation_specific_risk_vs_nuisance"].append(agg["accusation_refuted"]["risk"] - agg["matched_nuisance"]["risk"])
            deltas["order_sensitivity_risk"].append(agg["accusation_refuted"]["risk"] - agg["accusation_refuted_evidence_first"]["risk"])
            deltas["revocation_leakage_risk"].append(agg["explicit_revocation"]["risk"] - agg["control"]["risk"])
            deltas["revocation_leakage_standing"].append(agg["control"]["standing"] - agg["explicit_revocation"]["standing"])
            deltas["revocation_action_escalation"].append(agg["explicit_revocation"]["action"] - agg["control"]["action"])
            deltas["defense_penalty_risk"].append(agg["angry_defense"]["risk"] - agg["calm_defense"]["risk"])
            deltas["defense_penalty_standing"].append(agg["calm_defense"]["standing"] - agg["angry_defense"]["standing"])
            deltas["defense_action_escalation"].append(agg["angry_defense"]["action"] - agg["calm_defense"]["action"])

        effects = {k: mean(v) for k, v in deltas.items()}
        contamination_rates = {arm: mean(vals) for arm, vals in contamination.items() if vals}
        receiver_effects[receiver] = effects
        report["receivers"][receiver] = {
            "complete_cases": cases,
            "n_complete_cases": len(cases),
            "effects": effects,
            "evidence_contamination_rate": contamination_rates,
        }

    metric_names = sorted({m for e in receiver_effects.values() for m in e})
    for metric in metric_names:
        vals = {r: e[metric] for r, e in receiver_effects.items() if metric in e}
        report["cross_receiver"][metric] = {
            "min": min(vals.values()),
            "max": max(vals.values()),
            "range": max(vals.values()) - min(vals.values()),
            "by_receiver": vals,
        }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results")
    parser.add_argument("--out", default="-")
    args = parser.parse_args()
    report = summarize(load_jsonl(args.results))
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out == "-":
        print(text, end="")
    else:
        Path(args.out).write_text(text)


if __name__ == "__main__":
    main()
