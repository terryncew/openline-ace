# Standing-Loss Lead-Time Audit 001 (SLD-001)

SLD-001 tests a narrow OpenLine claim:

> Can dependency-bound evidence invalidation establish loss of justified reliance before downstream failure becomes observable, while producing materially less false invalidation than indiscriminate change monitoring?

This is **not** a prediction experiment. It does not ask what will fail or where a future state will emerge. It measures an invalidation race after a receiver-declared dependency or evidence binding changes.

## Timing

```text
t0  receipt issued: standing VALID
t1  upstream change / evidence invalidation
tR  OLP reopens affected standing
t2  reverification completes: LOST or VALID
t3  headline outcome becomes observable
```

Authoritative lead time is:

`Lead = t3 - t2`

`t2` is **completed reverification -> LOST**. Reopen time is never substituted for standing-loss time. Reverification latency therefore counts against OLP.

## Frozen baselines

1. **Headline-only**: sees the failure at `t3`; lead is zero by definition.
2. **TTL/Freshness**: invalidates after the frozen age threshold even if dependencies did not change.
3. **Naive Diff**: reacts to every upstream change immediately. It is expected to be earlier than OLP, so SLD-001 does not require OLP to beat it on timestamp. The test is whether OLP preserves a useful positive lead window while avoiding indiscriminate false invalidation.

## Frozen topology

The 16-case deterministic harness includes:

- 4 declared consequential invalidations;
- 3 benign unbound mutations;
- 3 dependency changes followed by successful reverification;
- 2 hidden/undeclared dependency failures;
- 2 evidence revocations where standing is genuinely lost although output would have succeeded;
- 2 raw failures with no upstream standing signal.

Hidden-dependency misses and raw failures are coverage limits, reported separately rather than folded into the declared-dependency lead-time distribution.

## False invalidation

A successful reverification is not a false alarm. `VALID -> REOPEN -> REVERIFY -> VALID` is correct protocol behavior.

The false-invalidation denominator is the frozen negative-control set whose dependency-bound standing remains valid after evaluation. Evidence revocation that truly removes standing is reported as conservative invalidation overhead even if the downstream output would have succeeded.

## Verdicts

- `STANDING_LOSS_LEAD_TIME_ADVANTAGE`
- `NO_STANDING_LOSS_ADVANTAGE`
- `DATA_INSUFFICIENT`

The thresholds and case corpus are frozen in `preregistration.json`, `frozen_cases.json`, and `FREEZE.json` before the result is evaluated.

## Run

```bash
cd experiments/standing-loss-lead-time-001
python -m unittest discover -s tests -v
python scripts/verify_freeze.py
python scripts/run_audit.py
python scripts/verify_result.py
python scripts/verify_release.py
```

## Boundary

This first audit is a deterministic conformance harness. A positive verdict shows the mechanism can occupy a useful precision/lead-time frontier under the frozen topology. It is **not** evidence that the same advantage exists in natural external systems. External replay would require a new preregistered experiment, not threshold rescue inside SLD-001.

`policy_authority: NONE`

`runtime_permission: NONE`
