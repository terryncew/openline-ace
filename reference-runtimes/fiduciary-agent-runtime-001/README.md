# Fiduciary Agent Runtime 001

A reference OpenLine assurance runtime for agentic code changes.

The agent may propose, learn, and act. It may not manufacture the evidence or authority that lets its own action pass.

This runtime composes the architectural roles already exercised elsewhere in OpenLine without pretending they are one trusted controller:

`generate -> independent evaluation -> consequence evidence -> mandate check -> COMMIT / QUARANTINE / DENY -> receipt -> dependency retention -> standing-loss reopen`

## Hard invariant

Three powers remain separate:

1. **Proposal power** — the coding agent may create candidate patches and generator revisions.
2. **Evidence power** — task, meta, and consequence evaluators attest to bounded facts about a proposal.
3. **Authority power** — the principal/mandate issuer determines what actions are permitted; the receiver Gate alone decides whether the consequence is admitted.

A successful evaluation does not authorize execution. A mandate does not prove a proposal is good. A previous COMMIT does not keep itself legitimate after a dependency loses standing.

## Generator mutations

Any change to shared proposal-shaping surfaces is conservatively classified as `TIER2_GENERATOR`, regardless of what the proposer calls it. Generator changes require a separate `META_EVALUATION` receipt in addition to task evidence, consequence evidence, and mandate standing.

## Reference coding-agent contract

A proposed repository action is bound to:

- proposal ID and payload hash;
- exact changed paths;
- task-evaluation receipt;
- consequence receipt;
- principal mandate;
- meta-evaluation receipt when the proposal changes the generator/search substrate.

The Gate returns one disposition: `COMMIT`, `QUARANTINE`, or `DENY`.

## Run

```bash
cd reference-runtimes/fiduciary-agent-runtime-001
python scripts/release_check.py
```

The demo first commits a valid independently evaluated patch, then invalidates the task-evidence receipt and shows the historical decision reopening.

## What this is not

This is a composition/reference runtime, not a claim that HMAC keys, an in-memory ledger, or the included coding fixture are production-safe. Production adapters should replace the reference signer registry, wallet/mandate store, receipt ledger, consequence evaluator, and claim graph with the corresponding hardened OpenLine modules.
