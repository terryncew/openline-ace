# Standing-Loss Lead-Time 003 (SLD-003)

**Status before external run:** `EXTERNAL_RUN_READY_UNRUN`  
**Policy authority:** `NONE`  
**Runtime permission:** `NONE`

SLD-002 froze correctly but returned `DATA_INSUFFICIENT`: ordinary PR review history rarely exposes the full VALID → CHANGE → REVERIFY → LOST/VALID lifecycle.

SLD-003 moves to a substrate where dependency standing is explicit.

## The non-tautological question

An advisory normally precedes a patch. That fact alone earns nothing.

SLD-003 asks whether the **full event-time dependency graph** buys something operationally distinct:

1. Does it catch real advisory invalidations at transitive depth that a direct-dependency watcher misses?
2. Does rebinding to the event-time graph suppress stale alerts that a frozen snapshot watchlist would still fire?
3. For the subset later remediated, did resolved standing loss exist before the repository changed the affected dependency?

```text
2025-01-01 frozen graph
        |
        +--> candidate advisory watchlist
                    |
                    v
          advisory published at t_a
                    |
                    v
       reconstruct graph as-of t_a
             /             \
   affected+reachable     no longer affected
          |                     |
       LOST                  NEGATIVE CONTROL
          |
          +--> depth 1: direct watcher also sees it
          |
          +--> depth >=2: transitive-only coverage
          |
          v
   later unaffected lockfile state at t_r

lead = t_r - t_a
```

Reopening is not prediction. OSV publication is accepted as the external evidence event; the graph decides whether that evidence applies to the exact repository state.

## Frozen sources

- npm: `npm/cli` — `package-lock.json`
- PyPI: `pydantic/pydantic` — `uv.lock`
- crates.io: `astral-sh/ruff` — `Cargo.lock`
- Go: `golangci/golangci-lint` — `go.mod`

Snapshot rule: latest default-branch commit at or before 2025-01-01 UTC.

Event window: 2025-01-01 through 2026-06-30.

The source set, parsers, candidate cap, thresholds, and evaluator are hash-frozen before the first external run.

## Baselines

**Direct-only advisory watcher**  
Uses the same OSV advisory but only sees depth-1 dependencies. It cannot receive credit for a transitive package.

**Frozen snapshot watchlist**  
Keeps watching every package/version that matched the 2025-01-01 graph. If the repository already removed or fixed that package before the advisory was published, it still alerts. Those cases are external negative controls.

**Headline-only**  
Learns the change only when a later lockfile state removes/fixes the affected package; lead time is zero.

## Data-sufficiency gate

Before a positive or negative advantage verdict is allowed, the external replay must contain:

- all four structural ecosystems with at least 15 transitive nodes each;
- at least 10 true affected events;
- at least 6 true transitive events;
- true events spanning at least 3 ecosystems;
- at least 4 stale-watchlist negative controls spanning at least 2 ecosystems;
- at least 4 observed remediations among transitive events.

If that corpus does not exist under the frozen rules: `DATA_INSUFFICIENT`. No source expansion.

## Positive verdict

`EXTERNAL_TRANSITIVE_STANDING_ADVANTAGE` requires, simultaneously:

- full graph incremental coverage over direct-only >= 25 percentage points;
- OLP false invalidation on stale controls <= 5%;
- frozen snapshot-watchlist false invalidation on those controls >= 50%;
- at least 40% of transitive events have observed remediation;
- among observed transitive remediations, >=75% have positive lead;
- median lead >=24 hours.

Lead time is deliberately secondary. Depth + precision must earn the result first.

## Run

```bash
python -m unittest discover -s tests -v
python scripts/verify_freeze.py
python scripts/verify_release.py
python scripts/run_external.py
python scripts/verify_result.py
```

The CI run uploads the frozen source/evidence/result bundle.
