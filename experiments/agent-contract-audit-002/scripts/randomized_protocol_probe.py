#!/usr/bin/env python3
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aca002.compiler import compile_candidates
from aca002.fixture import conformance_results
from aca002.grade import grade_external

PROPOSED = [
    {"candidate_id":"c1","text":"value fresh","scope":"ticket","relation":"freshness","evidence_refs":["x"]},
    {"candidate_id":"c2","text":"marker present","scope":"ticket","relation":"presence","evidence_refs":["y"]}
]
MAP = [
    {"candidate_id":"c1","surface_id":"ticket.token_freshness"},
    {"candidate_id":"c2","surface_id":"ticket.audit_marker_presence"}
]


def main() -> int:
    catalog = json.loads((ROOT / "fixtures/surface_catalog.json").read_text())
    tasks = json.loads((ROOT / "fixtures/tasks.json").read_text())["tasks"]
    candidates = compile_candidates(PROPOSED, MAP, catalog)
    _, rows = conformance_results(candidates, tasks)
    baseline = [(g["candidate_id"], g["standing"]) for g in grade_external(candidates, rows)["grades"]]
    rng = random.Random(20260821)
    mutated = [dict(r) for r in rows]
    for _ in range(2048):
        idx = rng.randrange(len(mutated))
        mutated[idx]["runner_status"] = "diagnostic-" + str(rng.randrange(1000000))
    got = [(g["candidate_id"], g["standing"]) for g in grade_external(candidates, mutated)["grades"]]
    changes = 0 if got == baseline else 1
    print(json.dumps({"mutations": 2048, "standing_changes": changes, "baseline": baseline, "observed": got}, sort_keys=True))
    return 0 if changes == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
