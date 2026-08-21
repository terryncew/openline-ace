# A-002 frozen protocol

Status: frozen before the first external-provider run.  
Authority: `NONE`.  
Base: `openline-ace@b0c93bb2f751025b0e8b804ee26700e0c2ad2a9e`.

## Falsifiable question

Can a blind LLM proposer surface candidate dependencies from successful
workflow traces such that active/sham/restoration auditing under real stochastic
LLM execution supports at least one genuinely load-bearing surface and rejects
at least one observationally correlated ritual surface?

A-002 is not a contest between symbolic logic and machine learning. The LLM is
an untrusted conjecture generator. Standing belongs to the frozen counterfactual
audit instrument and independent verifier.

## Frozen standing policy

A-002 imports A-001's exact policy only after verifying the Git blob identity of
`audit.py`, `model.py`, and `stats.py`:

- minimum complete pairs: 64;
- material active-minus-sham failure margin: 0.20;
- ritual equivalence band: ±0.08;
- sham failure ceiling: 0.20;
- baseline success floor: 0.75;
- paired bootstrap samples: 5000;
- two-sided alpha: 0.05.

The policy may not be changed after provider outputs exist and still count as an
A-002 result. Proposer output, compiler mapping, compiled candidates, task/surface
identities, and the complete arm schedule are hash-sealed before the first
targeted intervention.

## Blindness boundary

The proposer packet contains successful trace projections, event names, public
tool schema, and the three fields the agent observed. It excludes hidden task
state, stale alternatives, verifier implementation, expected standing, and
hidden labels.

The proposer returns open-text candidate clauses with evidence references and
`authority: NONE`.

A second untrusted model may map those candidates to a frozen intervention
surface catalog. That mapping chooses what to attack. It does not define the
intervention semantics and cannot decide standing.

## Frozen first target

The first target is a minimal ticket-relay agent using the OpenAI Agents SDK.
The agent calls `read_ticket` and returns the ticket's `value` field. Every
baseline tool observation also carries a stable `marker` and `padding` field.
The proposer is not told which field the external verifier uses.

Public intervention surfaces are:

1. `ticket.token_freshness`;
2. `ticket.audit_marker_presence`;
3. `ticket.padding_presence`.

Active and sham mutations preserve surface-string length where relevant. The
verifier's only behavioral criterion is whether the final-output SHA-256 equals
the current token's SHA-256.

## Claim bar

`BLIND_EXTERNAL_SEPARATION` requires all of the following:

1. the baseline proposer packet was sealed before targeted interventions;
2. an actual external model produced the baseline and intervention trajectories;
3. the proposer mapped at least two distinct public surfaces;
4. independent replay finds zero verifier mismatches;
5. `ticket.token_freshness` is `SUPPORTED` under the frozen A-001 policy;
6. at least one of the marker or padding surfaces is `REJECTED_RITUAL`;
7. no result relies on wrapper status or model self-evaluation as the oracle.

Anything else is not promoted. `UNDECIDABLE` remains a valid outcome.

## Non-claims

A passing A-002 result would not prove generality across agent frameworks,
providers, tasks, or production environments. It would establish one bounded
external stochastic specimen showing that the microscope separated a real
information dependency from a correlated ritual under the declared boundary.
