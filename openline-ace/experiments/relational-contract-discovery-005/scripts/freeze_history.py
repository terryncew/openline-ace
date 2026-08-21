#!/usr/bin/env python3
"""Generate or check the label-bounded historical intervention table."""

from __future__ import annotations

import argparse
from pathlib import Path

from rcdl005.canonical import canonical_digest, canonical_json
from rcdl005.domain import ACTION_IDS, HYPOTHESES, signature

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "references" / "frozen-historical-interventions.json"


def payload() -> bytes:
    records = []
    for index, hypothesis in enumerate(HYPOTHESES):
        context_id = canonical_digest({"split": "development", "context": index})
        outcomes = signature(hypothesis)
        for action_id, active_failed in zip(ACTION_IDS, outcomes, strict=True):
            records.append(
                {
                    "context_id": context_id,
                    "action_id": action_id,
                    "active_failed": active_failed,
                    "sham_failed": False,
                }
            )
    records.sort(key=lambda item: (item["context_id"], item["action_id"]))
    document = {
        "schema": "rcdl.historical-interventions/0.5",
        "information_boundary": {
            "final_scenario_ids_available": False,
            "hypothesis_ids_available": False,
            "observable_class_labels_available": False,
            "one_context_per_candidate_mechanism": True,
            "action_ids_available": True,
            "active_outcomes_available": True,
            "sham_outcomes_available": True,
        },
        "records": records,
    }
    return canonical_json(document) + b"\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = payload()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != expected:
            raise SystemExit("frozen historical corpus differs from deterministic regeneration")
        print(canonical_digest(expected.decode("utf-8")))
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(expected)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
