# INTERVENTION-SUFFICIENCY-002

This experiment asks whether the already-frozen Unitree G1 counterfactual
corpus contains genuine state-specific intervention contrast.

It is a retrospective external replay. The source data and the earlier Stage B
result existed before this gate was frozen. A pass is therefore diagnostic: it
can justify a fresh confirmatory transition benchmark, but it cannot repair or
retroactively preregister the earlier result.

## Why 002 exists

INTERVENTION-SUFFICIENCY-001 required four trials per cell. That is appropriate
for stochastic evidence and wrong for an exact deterministic simulator branch.
Repeating one deterministic outcome four times creates no new evidence.

002 makes evidence mode explicit:

- `deterministic_rollout`: exactly one outcome per state/action/lag cell;
- `stochastic_rollout`: at least four independently indexed trials per cell;
- `validated_dynamics_model`: one probability per cell plus a pinned model
  validation receipt.

The scientific bar remains harder than completeness. The corpus must contain
matched apparent-risk states with different viable remedies, lag-driven action
loss, and enough state dependence that a global action-plus-delay rule cannot
explain the cells.

## Result

`INSUFFICIENT_STATE_SPECIFIC_INTERVENTION_CONTRAST`

The exact public Stage A corpus reproduced byte-for-byte: 50 contexts, six
actions, five lags, and 1,500 deterministic transition cells. The replay then
failed four frozen gates:

- global action-plus-delay accuracy was `0.9253` (maximum allowed: `0.85`);
- three bidirectional matched-risk remedy pairs were found (minimum: six);
- those pairs implicated three contexts (minimum: twelve); and
- four lag contractions were found (minimum: six).

All 30 action-lag strata varied across states, so the corpus is not literally
state-invariant. It still lacks enough balanced, state-specific contrast to
support a fresh transition claim. No transition confirmation or selector is
authorized.

The deterministic, stochastic, and validated-model controls also pass. A
complete deterministic corpus with one globally good remedy is rejected.

## Run locally

```bash
cd experiments/intervention-sufficiency-002
python scripts/release_check.py
```

The manual GitHub workflow regenerates the public, pinned Stage A corpus from
the upstream controller, verifies the known source hashes, and requires an
exact match with the committed external result.

## Decision

- `SUFFICIENT_FOR_FRESH_TRANSITION_CONFIRMATION`: freeze a new context holdout
  before outcomes and run the direct action-conditioned comparator again.
- `INSUFFICIENT_STATE_SPECIFIC_INTERVENTION_CONTRAST`: repair the intervention
  substrate or stop. A more elaborate controller is not a substitute.
- `INVALID_EXTERNAL_INTERVENTION_CORPUS`: an evidence pin or contract failed.

No verdict authorizes selector training or execution.
