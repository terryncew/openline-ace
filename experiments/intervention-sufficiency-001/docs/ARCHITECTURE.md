# Predictor, evaluator, selector, gate

The control path has four owners.

| Layer | Question | Output | Authority |
|---|---|---|---|
| Transition model | What follows from `(state, action, lag)`? | Recovery distribution with model and evidence receipt | `NONE` |
| Feasible-set evaluator | Which actions clear the frozen recovery threshold? | `FEASIBLE`, `INFEASIBLE`, or `UNKNOWN` per action | `NONE` |
| Policy selector | Which feasible proposal best preserves future action room? | Ranked proposal plus rejected alternatives | `PROPOSAL_ONLY` |
| Receipt Gate | Does the proposal have current evidence, standing, effect scope, and principal mandate? | `COMMIT`, `QUARANTINE`, or `DENY` | `RECEIVER_OWNED` |

The capacity objective may consider the size and durability of the successor
feasible set, sensitivity to lag, and dependence on one brittle escape path.
Those values remain model outputs. They never become self-executing permission.

INTERVENTION-SUFFICIENCY-001 sits before this pipeline. It checks whether the
corpus contains enough counterfactual contrast to test the transition model at
all. A pass admits a model tournament. It does not admit an action to the world.
