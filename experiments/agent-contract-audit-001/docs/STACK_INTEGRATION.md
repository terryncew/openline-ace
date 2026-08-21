# Stack Integration

A-001 belongs in `openline-ace` because it is a discovery/audit instrument.

It composes with the rest of the stack without changing their existing trust
boundaries:

```text
openline-agents / openline-langgraph / openline-otel
    capture traces and portable evidence
                 |
                 v
openline-ace / agent-contract-audit-001
    propose + attack candidate dependencies
                 |
                 v
candidate contract manifest (authority NONE)
          /                    \
         v                      v
openline-claim-graph      openline-receipt-gate
dependency consequences   receiver-owned appraisal
         \                      /
          \                    /
                 v
       optional Verified Commit /
       future static monitor compiler
```

`openline-otel` remains capture-only. It should not infer the contract.

`openline-agents` may provide trace and independently witnessed outcome material,
but A-001 does not modify its runtime control surface.

`openline-claim-graph` can represent the dependency after standing is earned and
later compute what should reopen if its evidence or basis changes.

`openline-receipt-gate` remains the receiver-owned authority boundary. A-001's
`SUPPORTED` standing is evidence, not permission.

No changes to those downstream repositories are part of A-001.
