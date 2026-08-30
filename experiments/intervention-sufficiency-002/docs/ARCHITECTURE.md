# Predictor, evaluator, selector, gate

002 remains upstream of every live control decision.

| Layer | Output | Authority |
|---|---|---|
| Transition model | `P(outcome | state, action, lag)` | `NONE` |
| Feasible-set evaluator | `FEASIBLE`, `INFEASIBLE`, or `UNKNOWN` | `NONE` |
| Policy selector | Ranked capacity-preserving proposal | `PROPOSAL_ONLY` |
| Receipt Gate | `COMMIT`, `QUARANTINE`, or `DENY` | `RECEIVER_OWNED` |

INTERVENTION-SUFFICIENCY-002 tests whether the evidence can support the first
layer. It neither implements the remaining layers nor lets one borrow authority
from another.
