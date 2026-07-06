# OpenLine ACE

ACE is an **Audited Conjecture Engine** for moving from anomaly to proof-ready claim.

ACE does not discover truth. It discovers candidates, attacks them, and turns survivors into proof-ready claims.

ACE exists because AI-assisted discovery has a dangerous failure mode: **a wrong frame can still predict**.

The first reference backend is the Ulam Clock Atlas. In the initial Ulam audit, an apparent moving pattern turned out to be a mistuned clock. The corrected frame exposed a collision wall, and the U(2,3) seed has now been promoted to a verified finite computational claim.

## Current benchmark

`certificates/ulam_23_finite_proof_package/` contains the U(2,3) 400k finite proof package.

Verified status:

- fast metric verification: `finite_certificate_verified`
- full greedy prefix-rule verification: `full_greedy_prefix_verified`
- finite prefix: 400,000 Ulam terms
- last value: 4,449,166
- counts mismatches: 0

## Repo layout

```text
ACE_DISCOVERY_LOOP_v0.md
ACE_PROMOTION_CHECKLIST.md
ace_config_v0.json
ace_discovery_loop_v0_receipt.json
benchmarks/
  ulam_23_400k_promotion/
certificates/
  ulam_23_finite_proof_package/
```

## Verify the U(2,3) finite certificate

Fast verification:

```bash
cd certificates/ulam_23_finite_proof_package
python3 verify_finite_certificate_u23_400k.py --fast
```

Full greedy prefix-rule verification:

```bash
cd certificates/ulam_23_finite_proof_package
gcc -O3 verify_ulam23_prefix_full.c -o verify_ulam23_prefix_full
./verify_ulam23_prefix_full
```

## Core line

ACE does not automate certainty.

It automates the discipline between anomaly and proof.
