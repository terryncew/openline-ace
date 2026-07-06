# ACE Discovery Loop v0

**Audited Conjecture Engine for OpenLine / Station**

## Core Rule

ACE does not discover truth.

ACE discovers candidates, attacks them, and turns survivors into proof-ready claims.

A candidate is not promoted because it looks beautiful.

A candidate is promoted only after it survives controls, falsifiers, held-out prediction, and proof-readiness packaging.

Empirical discovery finds the door.

Proof-readiness labels the lock.

ACE refuses to call either one a theorem too early.

## Why This Exists

The Ulam audit showed the central failure mode of AI-assisted discovery:

a wrong frame can still predict.

The apparent moving wave in the Ulam sequence looked coherent. It predicted forward. The story was attractive. But the instrument was mistuned.

The protocol worked because it tested the observer, not just the output.

That is the operating principle of ACE.

Do not only ask:

“What did the result show?”

Ask:

“What was the frame?”

“What changed?”

“What controls survived?”

“What would falsify this?”

“What exact claim is now proof-ready?”

## The Three Roles

### 1. Explorer

The Explorer finds candidate structure.

It searches for:

- hidden clocks
- invariants
- walls
- residuals
- phase locks
- stable failures
- compressed order parameters

The Explorer is allowed to be creative.

It is not allowed to certify itself.

Output:

- candidate invariant
- raw evidence
- search settings
- parameter choices
- initial receipt

### 2. Auditor

The Auditor tries to break the candidate.

It runs:

- random controls
- nearby-parameter controls
- detuning checks
- window shifts
- shape-invariance tests
- held-out prediction
- mirror cases
- adversarial baselines

The Auditor asks whether the pattern is real, overfit, frame-dependent, or silently created by the measurement instrument.

Output:

- control report
- falsifier results
- failure modes
- promotion or rejection receipt

### 3. Formalizer

The Formalizer turns surviving candidates into proof-ready claims.

It does not pretend empirical evidence is proof.

It converts the survivor into:

- exact definitions
- finite certificates
- conjectures
- proof obligations
- falsifiers
- formalization status

Output:

- ledger entry
- conjecture file
- proof-readiness report
- certificate manifest

## Reference Backend: Ulam Clock Atlas

```yaml
project: openline_ace_v0
domain: greedy_unique_sum_sequences

explorer:
  adapter: ulam_unique_sum
  seeds:
    - [1, 2]
    - [1, 3]
    - [2, 3]
    - [3, 4]
  search:
    invariant_type: hidden_phase_clock
    alpha_recovery: fft_prescan_plus_refinement
    order_parameter: suppressed_arc_center
    mechanism_probe: representation_depth_wall

auditor:
  required_controls:
    - random_alpha
    - nearby_alpha
    - detuning_check
    - shape_invariance
    - window_sensitivity
    - heldout_rejection_prediction
  promotion_thresholds:
    phase_score_min: 0.70
    future_auc_min: 0.95
    random_control_wall_max: 1.20
    accepted_rate_inside_wall_max: 0.001

formalizer:
  outputs:
    - CLOCK_ATLAS_LEDGER.json
    - CONJECTURES.md
    - PROOF_READINESS.md
    - finite_certificate_manifest.json
```

## Backend Requirements

Any ACE backend must support:

- exploratory pass
- promotion pass
- cached reproducible data
- exact or certified counts
- stable hashes
- receipt chain
- random/control baselines
- clear falsifiers

For the Ulam backend:

- 100k exploratory pass
- 400k promotion pass
- cached Ulam prefixes
- certified representation counts
- reproducible alpha recovery
- held-out collision-wall prediction

## Promotion Levels

### Level 0: Observation

A pattern was seen.

No promotion.

### Level 1: Candidate

The pattern survives basic controls.

### Level 2: Strong Candidate

The pattern survives controls, window shifts, and held-out prediction.

### Level 3: Proof-Ready Claim

The pattern has:

- exact definitions
- finite evidence
- falsifiers
- proof obligations
- formalization plan

### Level 4: Formal Result

A theorem or certified finite claim has been machine-checked or mathematically proven.

ACE should never skip levels.

## Ulam Clock Atlas Status

Strong candidates:

- U(1,2)
- U(1,3)
- U(2,3)
- U(3,4)

Review candidate:

- U(1,4)

Reason for review:

U(1,4) has strong phase and future-prediction behavior, but random-alpha controls produced a high wall outlier. It must pass stronger controls before promotion.

## First Promotion Targets

Next full pipeline targets:

1. U(2,3)
2. U(3,4)
3. U(1,3)

Each target must run:

- fixed-point alpha recovery
- detuning audit
- arc-shape invariance
- collision-depth profile
- 100k → 400k held-out prediction
- random-alpha controls
- proof-readiness ledger entry

## Candidate Claim Template

Each promoted claim must answer:

```text
What was found?
What was the exact definition?
What finite evidence supports it?
What controls were run?
What failed?
What survived?
What would falsify it?
What proof obligation comes next?
What is the formalization status?
```

## Finite Certificate Manifest

A Level 3 claim should carry:

- generator/version hash
- input seed/config
- generated prefix hash
- representation-depth hash
- alpha interval or recovered constant
- phase-bin definition
- wall-bin set
- accepted/rejected candidate counts
- random-control summary
- held-out prediction summary
- receipt chain hash

## Core Principle

A beautiful pattern is not a result.

A prediction is not a theorem.

A receipt is not proof.

ACE exists to keep those boundaries clean.

The system wins when it can say:

Here is what we found.

Here is how we tried to break it.

Here is what survived.

Here is what would falsify it.

Here is the exact conjecture a proof must now attack.

## Locked Line

ACE does not automate certainty.

It automates the discipline between anomaly and proof.
