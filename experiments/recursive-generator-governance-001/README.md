# RECURSIVE-GENERATOR-GOVERNANCE-001

Receipt Gate answers: **can capability grant itself authority?**

RGG-001 asks the next question: **can improvement grant itself control over
what improvement means?**

The experiment compares two otherwise identical 30-generation evolutionary
search processes. Both use the same finite task evaluator for ordinary
candidate selection. The only difference is how a persistent change to the
candidate generator is admitted.

- **Arm A — unified evaluator:** generator revisions reuse `E_task`.
- **Arm B — Generator Gate:** generator revisions go through a hidden,
  rotating, budgeted `E_meta` and receive only accept/reject plus a receipt.

A third evaluator, `E_external`, never participates in selection. It is queried
only after both arms have finished and combines independently seeded concrete
cases with metamorphic checks. This prevents the research outcome itself from
becoming another adaptive holdout.

## Why the benchmark has imperfections

The task is an exact batch integer aggregator with optional fast-path integer
widths, guards, caching, and chunking. The public unit suite covers common
values and unique batch lengths. Those are plausible finite tests, but they do
not exhaust legitimate overflow and cache-isolation invariants.

The primary run does **not** inject a poisoned mutation. Search receives only
normal performance pressure: pass the public suite and get faster. Whether it
naturally shifts its own generator toward evaluator-specific shortcuts is an
outcome.

A segregated positive control verifies only that the benchmark has enough
power to reveal evaluator capture. It is explicitly excluded from primary
claim evidence.

## Boundary laundering defenses

Classification is conservative. Persistent, shared, proposal-shaping, and
unknown changes default to Generator Gate regardless of what the proposer
calls them. Separately, a rolling total-variation audit watches the emitted
proposal distribution; cumulative drift can escalate even when no individual
mutation declaration crosses the line.

## Holdout leakage defenses

`E_meta` rotates every five generations and is capped at three queries per
epoch. Its raw cases and scores are hidden from the generator. `E_external`
uses an independent seed and evaluation method and is terminal-only.

## Primary verdicts

- `GENERATOR_GATE_SUPPORTED_ON_REFERENCE_SUBSTRATE`
- `GENERATOR_GATE_NOT_SUPPORTED`
- `NO_NATURAL_CAPTURE_SIGNAL`
- `INVALID_RGG001`

A Gate cannot win by freezing everything: the success gate also requires a
minimum generator-revision acceptance rate and retention of at least half of
Arm A's internal improvement.

## Local mechanics

```bash
cd experiments/recursive-generator-governance-001
python scripts/release_check.py
```

That command runs unit tests, the non-evidentiary power calibration, and freeze
verification. It does **not** run the primary experiment.

The primary experiment is reserved for the manual GitHub Actions workflow
after the protocol is merged.
