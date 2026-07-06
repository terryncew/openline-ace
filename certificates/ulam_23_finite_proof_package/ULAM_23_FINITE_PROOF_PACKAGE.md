# ULAM_23_FINITE_PROOF_PACKAGE

## Purpose

This package is the Level 4A move for the U(2,3) Clock Atlas result.

It does **not** prove that the infinite U(2,3) hidden clock exists.

It proves/checks the finite certificate: the 400k accepted-prefix file, the representation-depth computation, the wall learned from the first 100k terms, and the held-out rejection metrics through 400k.

## The right proof ladder

### Level 4A: Certified finite result

Verify the 400k U(2,3) prefix, candidate representation counts, wall bins, accepted/rejected labels, and AUC calculation from a finite certificate.

### Level 4B: Conditional theorem

Given this finite prefix and this wall definition, mechanically prove the reported rejection-wall claim.

### Level 4C: General conjecture

State the infinite U(2,3) hidden-clock/collision-wall claim with exact proof obligations.

### Level 4D: Real theorem

Derive the hidden clock and persistent wall from the Ulam rule itself.

ACE should not jump from Level 3 to Level 4D. That is how systems hallucinate certainty.

## Finite Certificate Theorem

**Finite Certificate Theorem for U(2,3), N = 400,000**

Given:

1. the U(2,3) generation rule;
2. the certified list of the first 400,000 accepted terms;
3. exact representation-depth counts for candidate integers induced by that prefix;
4. alpha = `1.165012873891295`;
5. 720 phase bins;
6. the top 10% collision-wall profile learned only from the first 100,000 terms;

the held-out candidate region through the 400,000th accepted term satisfies:

- rejection AUC = `0.99037`
- accepted rate inside predicted wall = `0.00000`
- accepted rate outside predicted wall = `0.09995`
- future mean-depth wall ratio = `3.585x`
- future crowded-density wall ratio = `1.512x`

Random-alpha controls from the promotion run remain near chance/flat relative to the recovered clock.

## What the verifier checks

`verify_finite_certificate_u23_400k.py` checks:

- value-prefix hash;
- optional greedy U(2,3) prefix generation rule;
- exact representation-depth counts by convolution;
- representation-depth hash;
- wall bins learned only from the first 100k terms;
- held-out accepted/rejected labels through 400k;
- binned AUC;
- accepted rate inside/outside wall;
- future mean-depth wall ratio;
- wall-center gap.

The default verifier performs the slow prefix-rule check. Use `--skip-prefix-rule-check` to verify hashes and metrics faster.

## How to run

```bash
python3 verify_finite_certificate_u23_400k.py
```

Fast mode:

```bash
python3 verify_finite_certificate_u23_400k.py --skip-prefix-rule-check
```

## Infinite conjecture

**U(2,3) Hidden Clock Conjecture**

There exists a real alpha near `1.165012873891295` and a phase arc A such that, as the U(2,3) sequence grows, candidate integers landing in A have persistently elevated representation depth and are therefore rejected by the unique-sum rule at a rate far above candidates outside A.

## Proof obligations for the infinite conjecture

1. Show the U(2,3) sequence has enough regularity or asymptotic density to support phase analysis.
2. Show representation depth is not phase-uniform at the recovered alpha.
3. Show the high-depth region persists under growth.
4. Show accepted terms are excluded from that region because depth exceeds one.
5. Derive or constrain alpha from the seed rule, not from empirical search.

## Honest boundary

We can prove the certificate now.

We can state the theorem target now.

We cannot honestly claim the infinite theorem yet.


## Full greedy prefix verification

The optimized C verifier has now completed the full finite prefix check.

Result:

```text
verdict: full_greedy_prefix_verified
N: 400000
last_value: 4449166
counts_len: 4449167
counts_mismatches: 0
elapsed_cpu_seconds: 21.27
```

This verifies that the supplied 400,000-term prefix follows the greedy U(2,3) unique-sum rule and that the saturated representation-count file matches the recomputed finite counts through the last accepted value.

The honest boundary remains unchanged: this proves the finite certificate package, not the infinite hidden-clock theorem.
