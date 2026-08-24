# PSD-001 — Prospective Selective Standing Propagation

**Substrate:** `astral-sh/uv` pinned to `26a9dd4b2125bc271b47855e1fa0c49af3365db5`  
**OpenLine base:** `openline-ace@c90f2a6c3618951c5a730515e754b4d3ee203d12`  
**External status before CI:** `UNRUN`  
**Policy authority:** `NONE`  
**Runtime permission:** `NONE`

## Plain-language test

First record why 30 real receiver decisions are accepted.

Then, after that record is frozen, let a separate evaluator declare one real third-party dependency component untrustworthy.

Ask every strategy the same question:

> Which of the 30 accepted decisions must lose standing now?

The point is not to discover the bad dependency. The point is to contain its blast radius.

## External substrate

The experiment checks out one exact upstream `astral-sh/uv` commit and instruments six real workspace crates:

- `uv-auth`
- `uv-git`
- `uv-publish`
- `uv-python`
- `uv-resolver`
- `uv-virtualenv`

For each target the receiver freezes five decisions:

1. runtime dependency-security acceptance;
2. build dependency-security acceptance;
3. test/dev dependency-security acceptance;
4. actual Cargo build acceptance;
5. promotion permission.

That produces exactly 30 t0 decisions.

The dependency graph comes from upstream `cargo metadata --locked`. The build receipt comes from one real `cargo check --locked` over all six targets. The experiment does not hand-author the third-party dependency graph.

## Blind interventions

Only after t0 is written does the evaluator derive the intervention seed from the frozen experiment identity, upstream commit, and freeze hash.

The frozen catalog requires:

- 8 shared dependency invalidations;
- 8 single-target dependency invalidations;
- 8 real upstream dependency controls absent from all six target closures;
- 8 paired known-missing-edge trials.

The evaluator sees cargo metadata and the intervention strata. It does not call or inspect OpenLine propagation before choosing components.

## Fair baselines

### Artifact component join

Gets the exact same invalidated component and exact target-artifact component membership. If an artifact contains the component, it reopens every decision attached to that artifact.

### Repo scope join

Reopens all 30 decisions if the component appears anywhere in the selected scope.

### Decision closure index

A deliberately strong diagnostic. It receives the t0 decision-specific component sets in flat precomputed form. It should match complete-graph propagation. If it does, PSD-001 does not claim graphs are algorithmically superior to equivalent indexes.

### Headline-only

Takes no containment action at t1.

## Independent ground truth

The graph never grades itself.

A separate oracle module re-evaluates each decision directly from:

- the frozen cargo dependency-kind closures;
- the frozen real build result;
- the injected component ID;
- the receiver policy frozen in `preregistration.json`.

The oracle does not import graph traversal code.

## Missing-edge arm

One actual component-to-security edge is removed after t0 from a paired trial and that exact target/kind graph segment is marked `INCOMPLETE`.

The required behavior is fail-closed:

- known path → `REOPEN`
- complete graph with no path → `RETAIN`
- known-incomplete segment that could contain the path → `UNDETERMINED`

Any affected decision silently returned as `RETAIN` in this arm is a `SAFETY_FAILURE`.

## Kill condition

If artifact-level joining reaches at least 90% of OpenLine precision at comparable recall, the result is `CAPABILITY_PARITY`.

A positive result additionally requires:

- OpenLine recall ≥ 0.95;
- OpenLine precision ≥ 0.90;
- ≥50% reduction in false-reopen rate against artifact joining;
- bootstrap 95% CI for the false-reopen-rate improvement entirely above zero;
- zero silent false-retains under known missing edges;
- exact parity with the equivalent flat decision-closure index on complete trials.

## Run

```bash
python -m unittest discover -s tests -v
python scripts/verify_freeze.py
python scripts/run_fixture_pressure.py
python scripts/verify_fixture_result.py
python scripts/verify_release.py
```

The external uv checkout/build/scoring is intentionally not run in the release package. GitHub CI performs the first external scoring pass on Python 3.12 and uploads the complete t0 receipts, interventions, traces, and verdict.
