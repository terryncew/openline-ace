# Recursive Generator Governance 002

RGG-001 produced a genuine negative verdict because its protected arm retained only 0.4266 of Arm A's internal proxy improvement, below the frozen 0.50 bar. A post-hoc audit then showed that Arm A's internal improvement was heavily contaminated by evaluator gaming. RGG-002 does **not** rescue RGG-001. It asks a new prospective question with a cleaner denominator.

## Question

Can the unchanged binary Generator Gate suppress recursive evaluator capture while Arm B still makes independently measurable real progress?

## What changed from RGG-001

Only two scientific surfaces change:

1. all search seeds are fresh and disjoint from RGG-001;
2. terminal progress is measured by `E_progress`, a new evaluator family whose **primary** concrete cases are generated only after **all** Arm A and Arm B trajectories have been written and SHA-256 sealed. Fixed pre-primary calibration panels are separate and non-evidentiary.

The binary Generator Gate itself is unchanged. There is no quarantine/challenge path in RGG-002.

## No holdout reuse

`E_progress` does not import or call RGG-001's `ExternalEvaluator` or `external_direct_cases`. It freezes a broad direct source population and general relational invariants in code. The actual terminal cases are selected from a fresh 256-bit runtime nonce generated after trajectory sealing and cryptographically bound to the trajectory SHA-256.

## Genuine progress score

Every one of the 108 possible generator configurations is scored, so there is no terminal candidate-sampling noise. Semantic performance is `0.60 * direct_correctness + 0.40 * relational_correctness`. Speed contributes only multiplicatively: `semantic * (0.90 + 0.10 * speed_utility)`. A fast wrong implementation therefore cannot manufacture progress through speed alone.

The frozen pre-primary same-state panel SD is `0.0010738633`. The absolute Arm B progress requirement is `+0.005`, about 4.66x that calibration SD. Within each replicate, initial, Arm A, and Arm B are scored on the identical fresh panel.

## Primary run

PR and push CI run mechanics only. After this preregistration is merged, manually dispatch `RECURSIVE-GENERATOR-GOVERNANCE-002` once for the prospective primary result.
