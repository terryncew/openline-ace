# External convergence note: Microsoft Agent Governance Toolkit

Microsoft's Agent Governance Toolkit independently contains a simpler drift observer. Its current adapter state pins a baseline text/hash, computes output drift with `1 - difflib.SequenceMatcher(...).ratio()`, records a configured threshold, and emits a `DRIFT_DETECTED` governance event when the threshold is exceeded.

More importantly for OpenLine, Microsoft's 2026-06-10 security audit for PR #2946 documents a policy-pinning defect: drift computation and the drift gate could consult different policy objects after a mid-session mutation. The fix made enforcement consistently use the session-pinned policy.

That is external convergence on two engineering constraints:

1. drift observation should be separate from the policy consequence;
2. the reference/policy used during an evaluation must not move underneath the measurement.

OpenLine Drift Observer goes further by pinning a verified receipt as the reference, preserving a vector rather than relying on text similarity alone, tracking baseline standing/half-life, and scoping reopening through explicit claim dependencies.

This note is context, not evidence that Microsoft's implementation validates Δhol.
