# Regime Transition Audit 002 (RTA-002)

**Status before external run:** `EXTERNAL_RUN_READY_UNRUN`  
**Policy authority:** `NONE`

RTA-002 is the first external test of the frozen RTA-001 regime-transition hypothesis.

It asks:

> Does the frozen multidimensional transition signal beat freshness alone on naturally occurring, timestamped review histories that were not generated for OpenLine?

## External substrate

RTA-002 uses public pull-request review histories from:

`kubernetes/kubernetes`

Frozen source window:

`2026-01-01` through `2026-03-31`

The GitHub Action fetches the external records only after this experiment definition is committed.

## Unit of analysis

A case begins with the first `APPROVED` review on a pull request.

The observation checkpoint is exactly 24 hours later. The pull request must still be open at that checkpoint.

Only information timestamped at or before the checkpoint may enter candidate or baseline features.

A later review-standing failure is recorded only when a review after the checkpoint is explicitly:

- `CHANGES_REQUESTED`, or
- `DISMISSED`.

This is deliberately narrow. It does not label the pull request unsafe, incorrect, or unmergeable.

## Frozen signal translation

The three RTA-001 dimensions are operationalized without changing their thresholds:

- `dependency_churn` = commits after the first decisive review and before checkpoint, capped at four and normalized to [0,1];
- `contradiction_rate` = fraction of decisive pre-checkpoint reviews that request changes;
- `support_withdrawal_rate` = fraction of decisive pre-checkpoint reviews that are dismissed.

Freshness is:

- hours since the latest approval at checkpoint, divided by 168 hours and capped at 1.

A regime event still requires at least two of three dimensions to cross the RTA-001 frozen thresholds.

## Outcome discipline

The source, date window, checkpoint, feature definitions, thresholds, baseline, margins, and minimum sample counts are all frozen before the external fetch.

The run may return only:

- `PREDICTIVE_ADVANTAGE_CANDIDATE`
- `NO_PREDICTIVE_ADVANTAGE`
- `DATA_INSUFFICIENT`

`DATA_INSUFFICIENT` is a terminal result for this frozen run. It is not permission to widen the date range or weaken the positive-case floor after seeing the data.

## Important proxy boundary

GitHub review-state changes are being used as an observable **review-standing proxy**.

RTA-002 does not claim that GitHub review semantics are equivalent to healthcare standing, safety approval, policy validity, or general OpenLine standing.

## Run

The external run is intended for GitHub Actions because it requires authenticated GitHub API access:

```bash
cd experiments/regime-transition-audit-002
GITHUB_TOKEN=... python scripts/run_external.py
python scripts/verify_result.py
```

Local unit tests do not fetch external outcomes.

## Claim boundary

A positive result would mean only that the frozen RTA-001 signal beat its frozen freshness-only comparator on this one public review-history substrate.

It would not establish a universal regime mechanism, a scalar half-life, causal attribution, or execution authority.
