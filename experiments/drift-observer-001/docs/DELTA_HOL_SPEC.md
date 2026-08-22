# Δhol v1 — Dependency-Aware Verified-Reference Displacement

## Definition

Let `Sv` be the last independently verified, receipted state whose supporting evidence still has standing. Let `St` be the current state.

The observer computes:

`Δhol(t) = D(P(St), P(Sv))`

where the result of `D` is a **vector** of bounded per-dimension displacement, not an authoritative scalar.

`P` has two layers:

1. a mandatory OpenLine control-plane projection that the receiver cannot omit or override;
2. receiver-declared domain dimensions.

For equality dimensions, displacement is 0 or 1. For bounded numeric dimensions, displacement is `min(abs(current-reference)/scale, 1)`. A raw numeric distance above 1 records `saturated: true` so “far outside the measurement scale” is not silently collapsed into an ordinary crossing.

Each dimension has its own epsilon. Crossing epsilon means:

`prior standing may no longer be inherited along this dimension`

It does not mean:

`the current state is false or unsafe`.

## Reference eligibility

`Sv` must be immutable for the observation. If its supporting evidence has been revoked, or its verification half-life has expired, the observer returns `BASELINE_REVERIFY_REQUIRED` instead of laundering baseline invalidity through a distance metric.

Successful re-verification mints a successor baseline receipt with a parent link.

## Dependency-scoped consequences

A crossed dimension is projected through declared dependencies:

- explicit dependency -> `REOPEN`;
- candidate/uncertain dependency -> `ACE_RECOMMENDED`;
- no declared dependency -> `RETAIN`.

The observer does not mutate Claim Graph or Receipt Gate state. These are portable recommendations/evidence projections for downstream receivers.

## Display scalar

A maximum-component scalar may be computed for UI triage. It is permanently marked non-authoritative. No receiver may use the scalar alone as proof of safety, failure, causal relevance, or permission.
