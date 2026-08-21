# Relational Contract Discovery 001

This ACE experiment tests whether candidate relational rules can be proposed
from successful behavior, broken one at a time, compared with matched shams,
and retained without giving the proposer authority to certify itself.

It is the second ACE backend. The Ulam backend asks whether a discovered
mathematical pattern survives hostile controls. This backend asks whether a
discovered operational relationship is necessary for declared external
behavior.

## Stack position

```text
OpenTelemetry traces
        |
        v
ACE Explorer -> bounded RCDL clauses
        |
        v
ACE Auditor -> active intervention + matched sham
        |
        v
Independent oracle -> local standing only
        |
        +--> contract projection for Receipt Gate (no authorization in this RC)
        +--> standing/evidence projection for Claim Graph
```

The discoverer proposes. The actuator breaks. The oracle judges. The projection
cannot raise its own authority.

## First calibration

The substrate is a deterministic three-node Raft micro-harness. Six frozen
safety candidates cover vote uniqueness, durable vote ordering, candidate-log
freshness, append-prefix matching, majority commit, and commit-before-apply. A
seventh, observationally stable audit-marker clause is a declared spurious
control: the miner must propose it and the independent oracle must reject it as
causally irrelevant.

Each candidate must survive:

- successful baseline support;
- targeted guard bypass;
- an energy-matched no-op sham;
- independent checks of election safety, leader completeness, log matching,
  and state-machine safety;
- node renaming, event-ID renumbering, and JSON-key reordering;
- held-out seeds; and
- exhaustive inclusion-minimal family reduction.

The negative control matters: baseline support is enough to propose a clause,
but never enough to grant it standing.

The official Ongaro `raft.tla` file is pinned by Git blob and SHA-256 identity.
It is not executed by TLC in this RC, and the micro-harness has no
machine-checked refinement mapping to it. That keeps this experiment at ACE
Level 1 even when the local calibration passes.

## Run

```bash
python3 -m unittest discover -s tests -v
python3 -m rcdl verify-reference
python3 -m rcdl verify-evidence
python3 -m rcdl calibrate --output calibration-out --trials 8
python3 -m rcdl verify-manifest calibration-out/contract-manifest.json
python3 -m rcdl verify-projection calibration-out/contract-projection.json
```

No third-party Python package is required.

To run only the proposal boundary over predeclared successful traces:

```bash
python3 -m rcdl mine-candidates \
  --clauses clauses \
  --traces successful-traces/*.json \
  --min-support 2
```

This command can propose or reject hypotheses by support. It has no oracle
input and cannot grant causal standing.

The exact OTLP attribute profile is documented in
[`docs/OTEL-BOUNDARY.md`](docs/OTEL-BOUNDARY.md).

The checked-in `evidence/experiment-receipt.json` binds the local calibration,
release checks, official-reference identity, and experiment source tree. The
`evidence/evidence-index.json` file closes the evidence set. Both are
self-attested experiment records, not independent certification; the separate
OpenLine audit handoff is the tester-side chain.

## Claim boundary

This experiment establishes only that the closed-loop instrument can recover
and causally test its frozen Raft candidates inside the declared micro-harness.
It does not establish open-ended rule discovery, cross-implementation
transport, LLM-workflow validity, formal bisimulation, or permission to govern
live actions.

RCDL earns a separate repository only after the ACE loop transports beyond
this calibration boundary.
