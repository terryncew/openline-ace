# Architecture

## Ports to the existing OpenLine stack

| Runtime role | OpenLine module / concept | Runtime responsibility |
| --- | --- | --- |
| proposal search | Generator Gate / swarm improvement | may propose ordinary and generator mutations; never self-authorizes |
| consequence evidence | ACE / RCDL | binds action-conditioned consequence evidence to the proposal |
| authority | Mandate / Policy Gate + Wallet | supplies principal-owned, revocable, scoped standing |
| execution membrane | Receipt Gate / Airlock | returns COMMIT / QUARANTINE / DENY |
| historical dependencies | Frame Ledger | retains the state/evidence a decision depended on |
| standing change | Claim Graph / Evidence Recall | selectively reopens downstream decisions |
| compaction | Half-Life | future adapter; must preserve decision-equivalent standing semantics |
| multi-receiver freshness | distributed Gate work | future adapter; local reference ledger is intentionally single-process |

## Constitutional seam

The runtime refuses four collapses:

- proposer == task/meta/consequence evaluator;
- evaluator == principal authority;
- receipt possession == current standing;
- historical COMMIT == permanent legitimacy.

A generator-level mutation also cannot bypass the meta evaluator merely by declaring itself operational. Shared proposal-shaping paths are classified by effect, not by label.
