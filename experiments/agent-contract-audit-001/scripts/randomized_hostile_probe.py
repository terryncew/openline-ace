from __future__ import annotations

import random
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aca001.audit import grade_audit
from aca001.conformance import build_fixture_results, fixture_candidates
from aca001.model import AuditPolicy


def standings(candidates, rows):
    return {
        g["candidate_id"]: g["standing"]
        for g in grade_audit(candidates, rows, AuditPolicy())["grades"]
    }


def main() -> None:
    rng = random.Random(1001)
    candidates = fixture_candidates()
    base_rows = build_fixture_results()
    expected = standings(candidates, base_rows)

    rows = list(base_rows)
    mutations = 2048
    for _ in range(mutations):
        index = rng.randrange(len(rows))
        row = rows[index]
        rows[index] = replace(
            row,
            runner_status=f"nuisance-{rng.randrange(1_000_000)}",
        )
    rng.shuffle(rows)

    got = standings(candidates, rows)
    mismatches = 0 if got == expected else 1
    print({
        "randomized_nuisance_mutations": mutations,
        "standing_mismatches": mismatches,
    })
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
