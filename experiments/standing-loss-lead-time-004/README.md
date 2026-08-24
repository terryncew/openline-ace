# SLD-004 — Selective Decision Standing Propagation

**Current phase:** `F0_FEASIBILITY_AND_FROZEN_HARNESS`  
**Scientific H1 status:** `UNADJUDICATED`  
**Policy authority:** `NONE`  
**Runtime permission:** `NONE`

## Question

A strong scanner has already told us exactly what component/version became invalid.

Can OpenLine use a previously declared evidence-dependency graph to identify **which accepted decisions lose standing** and **which accepted decisions should remain standing**, without winning by simply reopening everything near the vulnerable component?

## Why F0 comes first

Historical replay is only meaningful if the public record contains:

1. a real, timestamped acceptance/promotion decision at `t0`;
2. an immutable artifact/build/release/configuration bound to that decision;
3. the evidence/dependency edges that allegedly justified the decision, documented no later than the external signal;
4. the external invalidation signal at `t1`;
5. at least one affected and one unaffected active decision in the same evaluation scope;
6. independent later truth at `t3` for every scored decision.

Git history plus a lockfile is not automatically an evidence DAG. A later patch is not automatically proof that every earlier decision was affected. SLD-004 fails closed on both shortcuts.

F0 freezes three historical probes before case completion: XZ 2024, event-stream 2018, and changed-files GHSL-2023-271. They may not be replaced because another incident is easier.

## Primary comparator

The headline baseline is **not** a repo-wide panic alert.

`artifact_component_join` gets:

- the same external scanner signal;
- the same exact affected component/version;
- exact component membership for each immutable decision artifact.

It reopens an active decision whenever that artifact contains the affected component/version.

OpenLine receives one additional structure only: the source-bound path stating that the invalidated evidence was actually part of the justification for that particular decision.

`repo_scope_flat_join` remains a diagnostic broad baseline.

## F1 success bar

F1 cannot run until a scoring cohort is independently frozen. It requires at least:

- 5 admissible cases;
- 30 decisions;
- 10 affected decisions;
- 10 unaffected decisions;
- 10 negative controls;
- every one of the five frozen negative-control categories;
- at least as many negative controls as affected decisions.

A positive result then requires:

- OpenLine recall >= 0.95;
- OpenLine precision >= 0.85;
- at least 50% lower false-reopen rate than the strongest recall-equivalent flat baseline;
- the flat baseline must not reach 90% of OpenLine's precision;
- the case-bootstrap 95% CI lower bound for the precision difference must be above zero;
- positive median `t3 - t1` opportunity window.

Anything else with sufficient data is `NO_SELECTIVE_STANDING_PROPAGATION_ADVANTAGE`.

## Run the frozen harness

```bash
python -m unittest discover -s tests -v
python scripts/verify_freeze.py
python scripts/run_fixture_pressure.py
python scripts/verify_fixture_result.py
python scripts/run_feasibility.py
python scripts/verify_release.py
```

Synthetic fixtures test the implementation only. They are excluded from every external claim.
