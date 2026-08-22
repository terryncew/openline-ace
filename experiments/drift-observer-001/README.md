# OpenLine Drift Observer 001 — Verified Continuity

This experiment salvages the useful operational core of Δhol without reviving Coherence Dynamics as a predictive theory.

The new definition is:

> **Δhol is dependency-aware verified-reference displacement.**

The observer compares the current state with an immutable verified baseline receipt. It produces a vector of per-dimension displacement. Threshold crossing means only that previously verified continuity may have been lost along that dimension. It does not mean the system is wrong, unsafe, or unauthorized.

## The pipeline

```text
verified baseline Sv
        |
        v
current state St
        |
        v
Δhol observer
changed dimensions + magnitude
        |
        v
dependency projection
        |
        +-- explicit dependency changed --> REOPEN
        +-- candidate dependency changed --> ACE_RECOMMENDED
        +-- unrelated change            --> RETAIN
```

Receipt Gate remains downstream. This experiment emits no runtime permission.

## What cannot be projected away

The receiver may declare domain dimensions, but the observer always checks a mandatory OpenLine control plane:

- reference receipt identity;
- policy hash;
- action binding;
- evidence bundle hash;
- evidence standing epoch;
- witness identity;
- witness version.

The receiver cannot redefine these dimensions or raise their thresholds.

## Why Δhol is a vector

The authoritative artifact is the per-dimension displacement vector. A scalar maximum is emitted only for dashboards and is explicitly marked `authoritative: false`. Different kinds of change are not allowed to cancel each other inside a single coherence score.

## Baseline half-life

A baseline is eligible only while its supporting evidence still has standing and its declared verification age has not expired. Expiration or revocation is not labeled “drift”; it produces `BASELINE_REVERIFY_REQUIRED`.

Successful re-verification mints a new baseline receipt linked to its parent. The old reference is never silently mutated or given a reset timer.

## Conformance falsifiers

The fixture requires all of these:

- README-only drift reopens `docs-reviewed` and leaves the unrelated merge claim standing.
- Patch/action rebinding reopens `merge-current-patch` and leaves the docs claim standing.
- Small sensor displacement stays within the declared envelope.
- Large sensor displacement reopens `control-stable`, records saturation, and sends an uncertain telemetry relation to ACE.
- Missing mandatory control-plane fields count as displacement.
- Expired or revoked baseline support reopens baseline-anchored claims without pretending a metric proved failure.

## Boundary

This is an observer/reopening conformance experiment. It does not establish that the chosen domain projection is complete, that a threshold is safety critical, that metric distance implies error, or that an ACE recommendation will discover a causal dependency.

`policy_authority: NONE`
`runtime_permission: NONE`
