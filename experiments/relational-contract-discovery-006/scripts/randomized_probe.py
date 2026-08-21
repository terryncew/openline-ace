#!/usr/bin/env python3
"""Randomized nuisance/transport audit over the frozen evaluation surface."""

from __future__ import annotations

import argparse
import json
import random

from rcdl006.execution import execute_queries
from rcdl006.fixtures import development_tasks, load_fixtures
from rcdl006.model import Split, Task
from rcdl006.policies import symbolic_decision, train_learned_policy


def run_probe(samples: int, seed: int = 6006) -> dict[str, int | str]:
    if samples < 1:
        raise ValueError("samples must be positive")
    fixtures = load_fixtures()
    examples = []
    for proposal in fixtures.by_split(Split.DEVELOPMENT):
        oracle = fixtures.oracle[proposal.proposal_id]
        examples.append((execute_queries(proposal, development_tasks()[0], "direct-v1"), oracle.standing))
    learned = train_learned_policy(examples)
    proposals = fixtures.by_split(Split.EVALUATION)
    rng = random.Random(seed)
    comparisons = 0
    mismatches = 0
    for index in range(samples):
        proposal = proposals[rng.randrange(len(proposals))]
        oracle = fixtures.oracle[proposal.proposal_id]
        token = rng.getrandbits(64)
        task = Task(
            task_id=f"probe-{index:05d}-{token:016x}",
            correct_patch=f"correct-{rng.getrandbits(40):010x}",
            alternate_patch=f"alternate-{rng.getrandbits(40):010x}",
            nuisance_seed=rng.randrange(1, 2**31),
        )
        transcripts = []
        for agent in ("ledger-v2", "queue-v2"):
            transcript = execute_queries(proposal, task, agent)
            transcripts.append(transcript)
            checks = (
                symbolic_decision(transcript).standing is oracle.standing,
                learned.decide(transcript).standing is oracle.standing,
                transcript.active.energy == transcript.sham.energy,
                transcript.sham.external_success,
                transcript.restoration.external_success,
                transcript.query_count == 3,
            )
            comparisons += len(checks)
            mismatches += sum(not check for check in checks)
        comparisons += 1
        mismatches += int(transcripts[0].signature() != transcripts[1].signature())
    return {
        "comparisons": comparisons,
        "mismatches": mismatches,
        "samples": samples,
        "seed": seed,
        "status": "PASS" if mismatches == 0 else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=512)
    parser.add_argument("--seed", type=int, default=6006)
    args = parser.parse_args()
    result = run_probe(args.samples, args.seed)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["mismatches"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
