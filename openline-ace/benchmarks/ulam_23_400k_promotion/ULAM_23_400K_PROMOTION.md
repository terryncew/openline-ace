# U(2,3) 400k ACE Promotion Run

## Verdict

`ulam_23_400k_promoted_to_proof_ready_claim`

This is the first non-classic Clock Atlas seed promoted through the full 400k ACE benchmark.

## Boundary

This is a promoted empirical claim, not a theorem. The run supports a proof-ready conjecture; it does not derive alpha from the Ulam rule.

## Recovered alpha

`1.165012873891295`

400k phase score: `0.829361`

## Collision wall

- mean-depth wall ratio: `3.589x`
- accepted-vs-log-depth correlation: `-0.86388`
- depth toward arc-center correlation: `0.90010`
- tail fit winner: `exponential`

## Held-out future rejection prediction

| train → test | future AUC | future wall | accepted inside wall | accepted outside wall | center gap |
|---:|---:|---:|---:|---:|---:|
| 100k → 200k | 0.99031 | 3.585x | 0.000000 | 0.100384 | 0.0° |
| 100k → 300k | 0.99034 | 3.585x | 0.000000 | 0.100034 | 0.5° |
| 100k → 400k | 0.99037 | 3.585x | 0.000000 | 0.099948 | 0.5° |

## Random-alpha controls

- random control count: `16`
- random mean AUC: `0.50010`
- random max AUC: `0.50076`
- random mean wall: `0.999x`
- random max wall: `1.001x`

## Shape invariance

- 50k window count: `8`
- corrected-alpha wall center span: `0.500°`
- corrected-alpha phase score range: `0.82912` to `0.82954`

## Proof-ready conjecture

For the Ulam sequence `U(2,3)`, there exists a recovered frequency alpha near `1.165012873891` and a phase arc A such that high-representation candidates concentrate in A, accepted terms are suppressed in A, and the wall learned from the first 100k terms predicts future rejection through 400k.

## ACE status

Level 3: proof-ready empirical claim.

Next move: finite certificate hardening and then repeat the same promotion pipeline for `U(3,4)` and `U(1,3)`.
