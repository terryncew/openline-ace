# Intervention outcome contract

Each JSONL row represents one rollout from a cloned pre-intervention snapshot.

Required fields:

| Field | Meaning |
|---|---|
| `schema` | `openline.ace.intervention-outcome.v1` |
| `dataset_id` | Stable identifier for the candidate corpus |
| `context_id` | One cloned integration state and policy-history state |
| `snapshot_sha256` | Hash of the complete snapshot bundle |
| `apparent_risk_bucket` | Frozen pre-outcome risk bucket used only for matched-risk pairing |
| `action_id` | Candidate intervention |
| `lag_ms` | Delay before intervention begins |
| `replicate` | Integer replicate index inside the cell |
| `trial_id` | Globally unique rollout identifier |
| `recovered` | Boolean frozen-target outcome |
| `target_sha256` | Hash of the recovery target and horizon |
| `policy_authority` | Must be `NONE` |

Rows sharing `context_id` must share the same snapshot, risk bucket, and target.
Every admitted context must contain every declared action at every frozen lag
with at least four replicates.

The risk bucket may deliberately omit directional state. Its purpose is to find
states that look equally dangerous to a scalar baseline while requiring
different remedies. The transition learner may later receive the richer state
representation; the sufficiency gate receives identifiers and outcomes only.
