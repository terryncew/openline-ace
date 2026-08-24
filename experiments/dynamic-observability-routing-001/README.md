# Dynamic Observability Routing 001 (DOR-001)

**Status:** `FROZEN_COMPLETE`  
**Policy authority:** `NONE`  
**Runtime permission:** `NONE`

DOR-001 tests an observability hypothesis, not a prediction hypothesis:

> Can verified prior evidence route a fixed measurement budget toward the channel that resolves an already-unfolding state sooner?

This line is deliberately separate from RTA. DOR never asks whether a transition signal forecasts later failure. It asks which measurement to request next when the receiver already knows that the current state boundary is unresolved.

## Pipeline

```text
verified receipt E_t
        |
        v
unresolved state boundary
        |
        v
receiver-owned ChannelManifest
        |
        v
DOR selects M_t+1
        |
        v
MeasurementReceipt
        |
        v
new observation E_t+1
        |
        v
ExternalOracle: resolved / unresolved
```

The `MeasurementReceipt` records the prior receipts used, selected channels, the routing reason, expiry, and exact telemetry budget. It cannot authorize execution and cannot declare the state resolved.

## Five pieces

- `ChannelManifest`: available measurements, cost, latency, provenance, resolution metadata, and mandatory sentinel coverage.
- `EvidenceState`: only receipts and observations available at or before time `t`; future evidence raises an error.
- `Router`: chooses the smallest admissible channel set inside the frozen budget.
- `MeasurementReceipt`: records why one channel was selected instead of the others; `runtime_permission: NONE`.
- `ReplayEvaluator`: compares DOR with fixed headline monitoring and equal-budget round-robin monitoring.

## The anti-cheat rule

`t_resolved` comes only from a frozen external oracle. DOR gets no credit for requesting a channel early, seeing a large value, or "yelling" before the evidence actually distinguishes the state under the oracle.

Every policy spends the same two-unit telemetry budget per tick and must always sample the cheap sentinel.

## Frozen deterministic harness

The held-out partition deliberately contains all three shapes:

- useful receipt-conditioned routing (`delta_tau > 0`);
- no advantage (`delta_tau = 0`);
- wrong-prior / blindness cases (`delta_tau < 0`).

It also contains a no-precursor case, a transition whose early precursor is outside the monitored manifest, and a nuisance-positive diagnostic channel. The router never receives the scenario truth, mechanism identity, reveal times, or oracle channel list.

## Result

DOR beat fixed headline monitoring on the primary held-out median by **1.5 ticks**, but it did **not** beat the equal-budget wide baseline: median `delta_tau_wide = 0.0`.

The frozen verdict is therefore:

`NO_ROUTING_ADVANTAGE`

This is useful. Receipt-conditioned routing can resolve some states substantially earlier, but DOR-001 does not establish that the frozen dynamic router allocates telemetry better than a simple equal-budget round-robin monitor across the mixed held-out mechanisms.

No weights, scenarios, baselines, or oracle rules may now be changed to rescue DOR-001.

## Run

```bash
python -m unittest discover -s tests -v
python scripts/run.py
python scripts/verify_result.py
```

If this line continues, a materially different router or a real external multichannel dataset belongs in DOR-002, not a repaired DOR-001.
