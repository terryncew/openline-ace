#!/usr/bin/env python3
"""Randomized-seed differential and combination probe for RCDL-003."""

from __future__ import annotations

import argparse
import json
from itertools import combinations

from rcdl.evaluator import evaluate
from rcdl.nuisance import nuisance_variants
from rcdl.otel import trace_from_otlp, trace_to_otlp

from rcdl003.contracts import (
    PLANNER_NOTE_HOOK,
    SPURIOUS_CONTROL_IDS,
    TARGET_CLAUSE_IDS,
    clauses_by_id,
    frozen_clauses,
)
from rcdl003.oracle import check_external_behavior
from rcdl003.replica import run_batch, run_pair


def probe(seeds: int) -> dict[str, object]:
    if isinstance(seeds, bool) or not isinstance(seeds, int) or not 1 <= seeds <= 10_000:
        raise ValueError("seeds must be an integer in [1, 10000]")
    mismatches: list[dict[str, object]] = []
    comparisons_count = 0
    clauses = frozen_clauses()
    by_id = clauses_by_id()
    target_hooks = sorted(by_id[item].hook for item in TARGET_CLAUSE_IDS)
    hook_sets = [*combinations(target_hooks, 2), tuple(target_hooks), (PLANNER_NOTE_HOOK,)]

    def check(condition: bool, **record: object) -> None:
        nonlocal comparisons_count
        comparisons_count += 1
        if not condition and len(mismatches) < 20:
            mismatches.append(record)

    for seed in range(seeds):
        for clause in clauses:
            active = run_pair(clause.hook, "active", seed)
            sham = run_pair(clause.hook, "sham", seed)
            active_eval = evaluate(clause, active.trace)
            sham_eval = evaluate(clause, sham.trace)
            active_oracle = check_external_behavior(active.outcome)
            sham_oracle = check_external_behavior(sham.outcome)
            is_target = clause.id in TARGET_CLAUSE_IDS
            is_control = clause.id in SPURIOUS_CONTROL_IDS
            check(not active_eval.passed, seed=seed, clause=clause.id, check="active_clause")
            check(sham_eval.passed, seed=seed, clause=clause.id, check="sham_clause")
            check(active_oracle.passed is (not is_target), seed=seed, clause=clause.id, check="active_oracle")
            check(sham_oracle.passed, seed=seed, clause=clause.id, check="sham_oracle")
            check(is_target or is_control, seed=seed, clause=clause.id, check="frozen_role")
            check(len(active.trace.events) == len(sham.trace.events), seed=seed, clause=clause.id, check="event_energy")
            for name, trace in (
                ("rename", nuisance_variants(active.trace)[0]),
                ("renumber", nuisance_variants(active.trace)[1]),
                ("reorder", nuisance_variants(active.trace)[2]),
                ("otlp", trace_from_otlp(trace_to_otlp(active.trace))),
            ):
                check(
                    evaluate(clause, trace).passed == active_eval.passed,
                    seed=seed,
                    clause=clause.id,
                    check=name,
                )
        for hooks in hook_sets:
            active = run_batch(hooks, active_hooks=hooks, seed=100_000 + seed)
            sham = run_batch(hooks, active_hooks=(), seed=100_000 + seed)
            active_failed = not check_external_behavior(active.outcome).passed
            sham_failed = not check_external_behavior(sham.outcome).passed
            predicted_active = any(
                not evaluate(by_id[item], active.trace).passed for item in TARGET_CLAUSE_IDS
            )
            predicted_sham = any(
                not evaluate(by_id[item], sham.trace).passed for item in TARGET_CLAUSE_IDS
            )
            expected_active = any(hook in target_hooks for hook in hooks)
            check(active_failed is expected_active, seed=seed, hooks=list(hooks), check="combination_oracle")
            check(predicted_active is active_failed, seed=seed, hooks=list(hooks), check="combination_prediction")
            check(not sham_failed, seed=seed, hooks=list(hooks), check="combination_sham_oracle")
            check(not predicted_sham, seed=seed, hooks=list(hooks), check="combination_sham_prediction")
            check(len(active.trace.events) == len(sham.trace.events), seed=seed, hooks=list(hooks), check="combination_energy")
    return {
        "schema": "rcdl.randomized-probe/0.3",
        "seeds": seeds,
        "comparisons": comparisons_count,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "verdict": "PASS" if not mismatches else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=256)
    args = parser.parse_args()
    result = probe(args.seeds)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
