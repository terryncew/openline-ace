from __future__ import annotations

import argparse
import random

from rcdl007.arena import EVALUATION_FAULTS, passive_observation, query_fn
from rcdl007.model import Scenario
from rcdl007.policies import symbolic_decide, train_learned_policy


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=4096)
    args = parser.parse_args()
    rng = random.Random(7007)
    learned = train_learned_policy()
    mismatches = 0
    for index in range(args.samples):
        faults = EVALUATION_FAULTS[rng.randrange(len(EVALUATION_FAULTS))]
        adapter = "ledger-v3" if rng.randrange(2) == 0 else "queue-v3"
        scenario = Scenario(f"random-{index:05d}", faults, rng.randrange(1, 2**31))
        passive = passive_observation(scenario, adapter)
        symbolic = symbolic_decide(passive, query_fn(scenario, adapter))
        learned_decision = learned.decide(passive, query_fn(scenario, adapter))
        if (
            symbolic.standing != learned_decision.standing
            or [event.probe_id for event in symbolic.queries]
            != [event.probe_id for event in learned_decision.queries]
        ):
            mismatches += 1
    print({"samples": args.samples, "mismatches": mismatches})
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
