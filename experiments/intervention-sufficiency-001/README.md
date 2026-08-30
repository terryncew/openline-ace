# INTERVENTION-SUFFICIENCY-001

This experiment asks one question before a state-conditioned controller is
allowed to train:

> Does the candidate evidence contain enough matched intervention contrast for
> state to matter?

A corpus clears the gate only when identical snapshots are branched across
multiple actions and delays, the grid is complete, similarly risky states
require different remedies, and feasible actions visibly disappear as lag
increases.

The gate prevents a common fake win: a model appears state-aware while merely
learning that one treatment usually works. It checks the evidence surface; it
does not fit a transition model, select an action, or authorize execution.

## Current standing

`MECHANICS_PASS_EXTERNAL_CANDIDATE_UNRUN`

Two deterministic controls are frozen:

- `global-rule-control` has complete action and lag coverage but one remedy
  works everywhere. It must be rejected.
- `state-specific-control` pairs states with the same apparent-risk bucket but
  opposite viable remedies and real lag contractions. It must clear the data
  gate.

Passing the second control proves only that the checker recognizes the declared
structure. A Unitree/MuJoCo or other external intervention corpus remains
scientifically unrun until its raw JSONL is supplied and hashed.

## Run

```bash
cd experiments/intervention-sufficiency-001
python -m unittest discover -s tests -v
python scripts/run_reference.py
python scripts/verify_result.py
python scripts/verify_freeze.py
```

Audit an external corpus without changing the frozen thresholds:

```bash
python scripts/audit_jsonl.py /path/to/intervention-outcomes.jsonl \
  --output /tmp/intervention-sufficiency-report.json
```

## Possible verdicts

- `SUFFICIENT_FOR_STATE_CONDITIONED_TRANSITION_TEST`
- `INSUFFICIENT_INTERVENTION_CONTRAST`
- `INVALID_INTERVENTION_CORPUS`

Even the first verdict authorizes only a held-out transition-model tournament.
It grants the transition model, feasible-set evaluator, and policy selector no
execution authority.
