# RCDL-007 audit dashboard

| Check | Frozen value |
| --- | --- |
| Verdict | `PRE_ADJUDICATION_CAUSAL_PARITY` |
| Claim effect | `UNIQUE_PRE_ADJUDICATION_UTILITY_NOT_FOUND` |
| Evaluation rows | 640 |
| Rows per policy | 320 |
| Symbolic accuracy | 320/320 |
| Learned accuracy | 320/320 |
| Symbolic probes | 544 |
| Learned probes | 544 |
| Mean probes | 1.7 each |
| Max probes | 2 each |
| Transport failures | 0 |
| Randomized nuisance comparisons | 4,096 / 0 mismatches |
| Hard budget | 4 |
| Policy authority | `NONE` |

The decisive boundary is pre-adjudication input custody. Evaluation policies
receive raw observations and opaque probe IDs, not artifact validity or hidden
standing.
