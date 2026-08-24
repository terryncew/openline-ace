# PSD-001 Claim Boundary

PSD-001 is a **prospective localization and containment** test.

It does not discover the upstream break. The external evaluator introduces a component invalidation **after** the 30 receiver decisions, evidence receipts, dependency closures, and evidence graph are frozen.

It does not test early warning, failure prediction, causal discovery, repair design, or fast tactical selection.

The primary comparison asks whether decision-specific evidence bindings prevent an artifact-level scanner signal from unnecessarily revoking orthogonal accepted decisions.

A positive result may support only:

> On the pinned `astral-sh/uv` workspace and frozen decision policy, decision-specific evidence binding preserved high affected-decision recall while materially reducing false reopening relative to artifact-level component joining, and known missing evidence failed closed rather than silently retaining affected decisions.

A positive result does **not** establish algorithmic uniqueness. `decision_closure_index` deliberately receives the same decision-specific component sets in flat form. If that index matches graph traversal, the result is about the value of **explicit decision-specific evidence binding and provenance**, not about graph traversal being mathematically superior to an equivalent precomputed index.

The receipt hashes in this audit are deterministic integrity bindings. Ed25519 signature security is not under test.

`policy_authority: NONE`  
`runtime_permission: NONE`
