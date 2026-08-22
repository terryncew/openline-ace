# Regime Transition Audit 001 (RTA-001)

**Status before execution:** `CONCEPT_ONLY_UNTESTED`  
**Maximum standing from the included synthetic fixture:** `PROTOCOL_CONFORMANCE_PASS_EXTERNAL_UNRUN`  
**Policy authority:** `NONE`

RTA-001 asks one bounded question:

> Can a pre-registered, multidimensional regime-transition signal predict later standing failure better than a simpler freshness-only baseline?

It does **not** assume that standing decays, that standing has a scalar half-life, or that a regime transition exists in every domain.

## Frozen design

The candidate signal has three separately reported dimensions:

- `dependency_churn`
- `contradiction_rate`
- `support_withdrawal_rate`

A transition event fires only when at least two dimensions cross their frozen thresholds in the same observation window. The implementation never turns those dimensions into a universal half-life score.

The simpler comparator uses only `age_since_last_verification`. It wins by default unless the candidate beats it on held-out balanced accuracy and Brier score by the preregistered margins.

The split is frozen before scoring: even `case_id` values are calibration; odd values are held out. No threshold may be retuned after outcomes are inspected.

## Synthetic-fixture ceiling

The bundled fixture exists only to test the instrument, failure codes, and comparator discipline. Even a perfect win can earn no more than:

`PROTOCOL_CONFORMANCE_PASS_EXTERNAL_UNRUN`

An external or naturally occurring time series, frozen before outcomes, is required before any predictive claim can advance.

## Failure codes

- `REGIME_SIGNAL_NOT_PREREGISTERED`
- `POST_OUTCOME_THRESHOLD_CHANGE`
- `SCALAR_HALF_LIFE_INFERENCE`
- `FRESHNESS_BASELINE_NOT_BEATEN`
- `INSUFFICIENT_HELDOUT_CASES`
- `FIXTURE_INTEGRITY_FAILURE`
- `EXTERNAL_VALIDATION_REQUIRED`

## Run

```bash
cd experiments/regime-transition-audit-001
python -m unittest discover -s tests -v
python scripts/run_audit.py
python scripts/release_check.py
```

## Claim boundary

RTA-001 does not grant execution authority, demote standing, reopen a decision, or predict failures in production. It is an ACE research instrument for deciding whether a regime-transition hypothesis deserves to advance beyond `CONCEPT_ONLY_UNTESTED`.
