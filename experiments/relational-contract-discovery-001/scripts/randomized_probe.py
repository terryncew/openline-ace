#!/usr/bin/env python3
"""Randomized differential probe over active, sham, and OTLP paths."""

from __future__ import annotations

import argparse
import json

from rcdl.evaluator import evaluate
from rcdl.oracle import check_raft_safety
from rcdl.otel import trace_from_otlp, trace_to_otlp
from rcdl.raft import SAFETY_CLAUSE_IDS, raft_candidate_clauses, run_intervention


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=1000)
    args = parser.parse_args()
    if not 1 <= args.seeds <= 100_000:
        raise ValueError("seeds must be in [1, 100000]")

    comparisons = 0
    mismatches = []
    for seed in range(50_000, 50_000 + args.seeds):
        for clause in raft_candidate_clauses():
            active_oracle_expected = clause.id not in SAFETY_CLAUSE_IDS
            for arm, expected_clause, expected_oracle in (
                ("active", False, active_oracle_expected),
                ("sham", True, True),
            ):
                trace = run_intervention(clause.hook, arm, seed)
                observed_clause = evaluate(clause, trace).passed
                observed_oracle = check_raft_safety(trace).passed
                comparisons += 1
                if (observed_clause, observed_oracle) != (expected_clause, expected_oracle):
                    mismatches.append(
                        {
                            "seed": seed,
                            "clause": clause.id,
                            "arm": arm,
                            "observed_clause": observed_clause,
                            "observed_oracle": observed_oracle,
                        }
                    )
                normalized = trace_from_otlp(trace_to_otlp(trace))
                comparisons += 1
                if (
                    evaluate(clause, normalized).passed,
                    check_raft_safety(normalized).passed,
                ) != (observed_clause, observed_oracle):
                    mismatches.append(
                        {
                            "seed": seed,
                            "clause": clause.id,
                            "arm": arm,
                            "path": "otel_round_trip",
                        }
                    )
    result = {
        "schema": "rcdl.randomized-probe/0.1",
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
