# Evidence contract

Every row binds one state/action/lag cell to one evidence mode.

Required base fields:

| Field | Meaning |
|---|---|
| `schema` | `openline.ace.intervention-outcome.v2` |
| `dataset_id` | Stable corpus identifier |
| `evidence_mode` | Deterministic, stochastic, or validated model |
| `context_id` | Exact cloned state/history identifier |
| `snapshot_sha256` | Hash binding physical and controller state |
| `apparent_risk_bucket` | Frozen, pre-outcome coarse risk projection |
| `action_id` | Candidate intervention |
| `lag_ms` | Delay before intervention |
| `replicate` | Trial index; zero for one-row evidence modes |
| `trial_id` | Globally unique evidence row |
| `target_sha256` | Frozen recovery target |
| `constraint_set_sha256` | Frozen physical/policy constraints |
| `policy_authority` | Must be `NONE` |

Mode-specific fields:

- deterministic and stochastic rows use Boolean `outcome_success`;
- validated-model rows use `success_probability` in `[0,1]` and a
  `model_validation_receipt_sha256`.

Deterministic and validated-model cells must contain exactly one row. A
deterministic row copied four times is invalid, not stronger evidence.
Stochastic cells require at least four unique replicates.

For the Unitree replay, apparent risk is the frozen perturbation-load bucket:

```text
force magnitude | absolute pitch torque
```

Direction, gait phase, actions, lags, and outcomes are excluded. The rule is
coarse on purpose: it asks whether similarly loaded states can require
different remedies. Because the rule was frozen after Stage A existed, the
result remains retrospective.
