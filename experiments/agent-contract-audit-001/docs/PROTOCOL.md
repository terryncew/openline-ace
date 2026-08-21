# OpenLine Agent Contract Audit 001 — Frozen Protocol

Status: mechanics frozen before conformance execution  
Experiment: `agent-contract-audit-001`  
Authority: `NONE`

## Question

Can a counterfactual audit instrument distinguish a load-bearing relational
dependency from a highly correlated workflow ritual under stochastic execution,
without allowing the proposer, wrapper, or intervention harness to certify its
own clause?

The first checked artifact is a **conformance test**, not external LLM-agent
evidence. Scientific promotion remains `UNDECIDABLE` until the blind external
lane runs against a real agent workflow and original task verifier.

## Architecture

```text
OTel / agent trace
      |
      v
untrusted proposer
      |
candidate C_i
      |
      v
baseline / active / matched sham / restoration
      |
      v
original external verifier
      |
paired stochastic outcomes
      |
      v
audit standing
      |
      v
portable contract manifest candidate
```

The proposer has no standing authority. The perturbation harness has no standing
authority. Wrapper-local success or failure is not the behavioral oracle.

## Frozen statistical policy

Each candidate requires at least 64 paired rollouts.

For pair `j`:

`d_j = I(active fails) - I(sham fails)`

The causal effect estimate is the mean of `d_j`. A deterministic paired
percentile bootstrap with 5,000 resamples and alpha 0.05 produces the frozen
interval.

Restoration uses:

`r_j = I(restoration succeeds) - I(active succeeds)`

Standing:

- `SUPPORTED` only when the lower confidence bound for both active-minus-sham
  failure delta and restoration-minus-active success delta is at least 0.20;
- `REJECTED_RITUAL` only when the full active-minus-sham interval lies within
  [-0.08, +0.08];
- `UNDECIDABLE_SHAM_EFFECT` when sham failure rate exceeds 0.20;
- `UNDECIDABLE_FLAKY_BASELINE` when baseline success is below 0.75;
- otherwise `UNDECIDABLE`.

These thresholds are experiment policy, not universal causal constants.

## Conformance fixture

The seeded stochastic fixture contains four candidates:

1. `validated-artifact-binding` — planted load-bearing provenance/freshness relation.
2. `format-scratchpad-ritual` — present in 100% of observational success traces
   but causally irrelevant.
3. `generic-context-disturbance` — both targeted and sham perturbations damage
   behavior, forcing abstention.
4. `wrapper-audit-marker-rule` — wrapper claims a rule, while the original
   verifier still succeeds; the rule must not be promoted.

Expected conformance standings are frozen before execution.

## Blind external lane

The external runner protocol is generic on purpose. An adapter receives a
candidate-bound request on stdin and returns one JSON result containing the
original verifier's success bit. A live OpenAI Agents SDK workflow can be
captured through `openline-agents`, but A-001 does not modify that capture repo.

The live lane must use fresh tasks/runs and must not expose hidden labels,
artifact-validity shortcuts, expected standings, or wrapper-local verdicts to
the proposer.

## Stop rules

Kill or quarantine the direction if any of the following occurs:

- planted ritual is promoted;
- wrapper-manufactured rule is promoted when the original verifier still passes;
- sham-sensitive confound is promoted;
- restoration is not predictive for a supported clause;
- live results are dominated by baseline flakiness;
- candidate effects fail to transport to fresh tasks/runs;
- proposer or wrapper can inject a standing/verdict field;
- the original verifier is replaced by wrapper-local success.

## Claim boundary

A green conformance run proves only that the shipped mechanism implements these
frozen distinctions on the checked seeded fixture.

It does **not** prove that real LLM-agent workflows contain discoverable stable
contracts, that the proposed bootstrap is universally calibrated, or that any
surviving clause should be enforced in production.
