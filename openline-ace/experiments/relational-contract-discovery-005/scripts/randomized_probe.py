#!/usr/bin/env python3
"""Random nuisance/action probe against the official deterministic oracle."""

from __future__ import annotations

import argparse
import json
import random

from rcdl005.domain import ACTION_BY_ID, ACTION_IDS, IMPLEMENTATIONS, behavior_preserved, final_scenarios
from rcdl005.execution import execute_pair


def run(samples: int) -> dict[str, object]:
    if not 1 <= samples <= 100_000:
        raise ValueError("samples must be between 1 and 100000")
    generator = random.Random(0x5CA11)
    scenarios = final_scenarios()
    mismatches = 0
    sham_failures = 0
    energy_mismatches = 0
    for _ in range(samples):
        scenario = scenarios[generator.randrange(len(scenarios))]
        action_id = ACTION_IDS[generator.randrange(len(ACTION_IDS))]
        expected_failed = not behavior_preserved(
            scenario.hypothesis.family, ACTION_BY_ID[action_id]
        )
        observed = []
        for implementation in IMPLEMENTATIONS:
            pair = execute_pair(scenario, action_id, implementation)
            observed.append(pair.active_outcome.failed)
            mismatches += int(pair.active_outcome.failed != expected_failed)
            sham_failures += int(pair.sham_outcome.failed)
            energy_mismatches += int(
                pair.active_outcome.energy_units != pair.sham_outcome.energy_units
            )
        mismatches += int(len(set(observed)) != 1)
    return {
        "schema": "rcdl.randomized-probe/0.5",
        "status": "PASS"
        if not mismatches and not sham_failures and not energy_mismatches
        else "FAIL",
        "samples": samples,
        "implementations": len(IMPLEMENTATIONS),
        "comparisons": samples * len(IMPLEMENTATIONS),
        "mismatches": mismatches,
        "sham_failures": sham_failures,
        "energy_mismatches": energy_mismatches,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=512)
    args = parser.parse_args()
    result = run(args.samples)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

