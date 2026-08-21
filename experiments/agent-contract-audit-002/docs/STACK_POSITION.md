# Stack position

```text
openline-agents / openline-otel
            trace capture
                |
                v
openline-ace / Agent Contract Audit
   propose -> attack -> sham -> restore
                |
        independent verifier
                |
        earned contract evidence
                |
       signed portable manifest
          /             \
         v               v
openline-claim-graph   openline-receipt-gate
reconsideration       receiver-owned policy
                           |
                           v
                    Verified Commit
```

A-002 remains in ACE because it is still proving the microscope. It does not
change `openline-agents`, `openline-otel`, Claim Graph, or Receipt Gate.

If an external stochastic result survives and later transports across a second
agent framework or provider, extraction into a dedicated `openline-contract-audit`
product repo becomes justified. Before that, a new repo would be premature.
