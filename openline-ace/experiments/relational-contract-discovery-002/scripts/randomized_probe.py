#!/usr/bin/env python3
"""Randomized active/sham, nuisance, and OTLP differential probe."""

from __future__ import annotations

import argparse
import json

from rcdl.evaluator import evaluate
from rcdl.nuisance import nuisance_variants
from rcdl.otel import trace_from_otlp, trace_to_otlp

from rcdl002.oracle import check_workflow_behavior
from rcdl002.workflow import (
    SPURIOUS_CONTROL_IDS,
    run_intervention,
    workflow_candidate_clauses,
)


def signature(evaluation) -> tuple[bool, int, int, int]:
    return (
        evaluation.passed,
        evaluation.trigger_count,
        evaluation.support_count,
        evaluation.violation_count,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=1000)
    args = parser.parse_args()
    if not 1 <= args.seeds <= 100_000:
        raise ValueError("seeds must be in [1, 100000]")
    comparisons = 0
    mismatches: list[dict[str, object]] = []
    for seed in range(50_000, 50_000 + args.seeds):
        for clause in workflow_candidate_clauses():
            active_oracle_expected = clause.id in SPURIOUS_CONTROL_IDS
            for arm, expected_clause, expected_oracle in (
                ("active", False, active_oracle_expected),
                ("sham", True, True),
            ):
                run = run_intervention(clause.hook, arm, seed)
                evaluation = evaluate(clause, run.trace)
                oracle = check_workflow_behavior(run.outcome)
                comparisons += 1
                if (evaluation.passed, oracle.passed) != (
                    expected_clause,
                    expected_oracle,
                ):
                    mismatches.append(
                        {
                            "seed": seed,
                            "clause": clause.id,
                            "arm": arm,
                            "path": "active_sham",
                        }
                    )
                normalized = trace_from_otlp(trace_to_otlp(run.trace))
                comparisons += 1
                if signature(evaluate(clause, normalized)) != signature(evaluation):
                    mismatches.append(
                        {
                            "seed": seed,
                            "clause": clause.id,
                            "arm": arm,
                            "path": "otel_round_trip",
                        }
                    )
                for index, variant in enumerate(nuisance_variants(run.trace)):
                    comparisons += 1
                    if signature(evaluate(clause, variant)) != signature(evaluation):
                        mismatches.append(
                            {
                                "seed": seed,
                                "clause": clause.id,
                                "arm": arm,
                                "path": f"nuisance_{index}",
                            }
                        )
    result = {
        "schema": "rcdl.randomized-probe/0.2",
        "seeds": args.seeds,
        "comparisons": comparisons,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:20],
        "verdict": "PASS" if not mismatches else "FAIL",
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
