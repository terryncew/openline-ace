# Relational Contract Discovery: what we built, why, and what RCDL-004 disproved

## The short version

Relational Contract Discovery asks a narrow engineering question:

> Which inclusion-minimal relationships must hold for a system to preserve a
> predeclared external behavior under a defined perturbation regime?

It is not a theory of everything and it does not output a coherence score. It
mines candidate relational clauses, tries to break them with targeted
interventions, compares those interventions with matched shams, tests recovery
and transport, and emits a bounded evidence manifest.

The fourth experiment found an important limit. A learned relational model
matched the frozen RCDL contract predictor perfectly on the deterministic
workflow substrate. RCDL's predictive result was real, but not unique.

## Where the idea came from

The original intuition was that a system's organization may live in persistent
relationships rather than in a single scalar state. That intuition overlaps
with computational mechanics, bisimulation, causal representation learning,
assume/guarantee contracts, temporal invariant mining, and work describing
computation through persistent relational constraints and recovery.

The useful contribution was therefore never “relations exist.” The useful
instrument is:

1. observe successful traces;
2. propose bounded relational rules;
3. intervene on each rule;
4. compare the intervention with a matched sham;
5. test recovery and held-out transport;
6. prune to inclusion-minimal contract families;
7. preserve evidence and limitations in a verifiable manifest.

The discoverer proposes. It never gets to declare itself correct.

## Why “the system remains itself” was removed

Identity is too elastic unless an external observer defines it. RCDL replaces
that phrase with behavioral compatibility against an independent contract:
tests, safety properties, authorized side effects, output constraints, latency,
or another observable specification.

There may also be several minimal implementations. Redundancy and substitution
mean the output must be a family of inclusion-minimal contracts, not one sacred
mechanism.

## The clause grammar

The search space is deliberately small:

- provenance: one artifact or event must derive from another;
- state conditioning: an action must depend on a current observation;
- ordering and exclusion: one event must precede another without a forbidden
  intervening mutation;
- information barriers: a channel may not expose protected state before an
  allowed phase.

This grammar prevents arbitrary first-order logic from turning the miner into
a tautology factory.

## Why sham interventions matter

Dropping a message can cause failure for boring reasons: fewer tokens, extra
latency, malformed syntax, or general prompt shock. A causal claim needs a
matched control that changes comparable nuisance energy while preserving the
candidate relationship.

The central comparison is:

`P(failure | break clause) - P(failure | matched sham)`

A candidate survives only when the targeted break changes external behavior,
the sham does not, restoration predicts recovery, the result transports, and
no proper subset performs equivalently.

## The calibration ladder

### RCDL-001: deterministic consensus

The first backend used Raft because its safety and liveness relationships are
known independently and faults are cheap to inject. The instrument had to
rediscover known clauses and reject a planted spurious temporal invariant.

### RCDL-002: deterministic repair workflow

The frozen engine moved to a rule-based planner, implementer, tester, and
reviewer loop. Four workflow clauses survived targeted interventions and one
planner-note correlation was rejected.

### RCDL-003: separate code path and bounded baselines

A separately written queue-driven implementation tested the frozen clauses on
unseen multi-fault combinations. RCDL predicted all 1,024 outcomes. The best
ordinary baseline missed 32 planner-note nuisance interactions. This supported
deterministic code-path transport, but the baselines were weak: they could not
learn generic equality joins and sequence structure.

### RCDL-004: learned relational pressure test

RCDL-004 removed that excuse. Learned models received generic event order,
cross-event equality, graph structure, and outcome labels. They still received
no clauses, hook names, intervention arms, oracle values at prediction time, or
raw artifact identities.

The strongest learned model was a multiple-instance relational DNF:

- split a trace into opaque task bags using identity equality;
- extract generic sequence and equality features from each task;
- learn one- or two-feature rules with zero observed negative support;
- retain every equally simple minimum-cost explanation;
- predict workflow failure when any task segment matches a learned failure
  rule.

It used 31 rules and classified all 1,024 final-audit traces correctly.

## The RCDL-004 result

| Predictor | Correct | Balanced accuracy | Failure F1 |
| --- | ---: | ---: | ---: |
| Frozen four-clause RCDL family | 1,024 / 1,024 | 1.000000 | 1.000000 |
| Learned relational rule set | 1,024 / 1,024 | 1.000000 | 1.000000 |

Verdict: `LEARNED_PARITY`.

The broad predictive-superiority claim is falsified within this tournament.
That is a successful experiment, not a software failure.

## Why the tie policy mattered

An early decision tree found a cheap shortcut: planner-note presence correlated
with failure in the single-fault training data. It scored perfectly on
validation but failed when a harmless planner-note perturbation appeared beside
a real fault.

A global minimum rule set made the same mistake. It chose two compact rules
that explained every training failure but depended on planner-note features.

The final learner retained all equally simple, high-precision explanations.
That preserved direct failure relations alongside the shortcut and transported
to the audit split. This is a small example of the larger representation
problem: one legible explanation may be an arbitrary member of an equivalence
class.

## The honesty boundary

The model design observed seeds 30000-30031 during development. Those traces
were removed from final scoring. The final audit used seeds 90000-90031,
selected after the algorithm and tie policy were frozen.

That is better than reusing the development set, but it is not strong external
independence. New seeds change opaque identities while preserving the same
deterministic fault semantics. The same builder wrote the workflow, model, and
test. No p-value is reported because deterministic seeds are not independent
samples from a population.

## What the result does and does not mean

The learned model reproduced prediction. It did not reproduce:

- targeted `do(not clause)` interventions;
- matched-sham comparisons;
- evidence that each retained relationship is necessary conditional on the
  others;
- recovery-horizon prediction;
- inclusion-minimal causal contract standing;
- an intervention plan for a new workflow.

So the surviving RCDL claim is narrower:

> RCDL may provide intervention-tested causal legibility and efficient
> falsification even when a learned trace model predicts equally well.

That claim remains unproved and should be allowed to fail.

## What comes next

The next discriminating test is not another accuracy tournament. Predictive
parity already answered that question on this substrate.

The useful RCDL-005 question would be:

> Given the same intervention budget, can RCDL identify which relation to break,
> predict recovery, and transport its explanation more efficiently and stably
> than a learned relational model?

An independent replication package is equally important because it attacks
shared-builder assumptions rather than classifier strength.

Only after those boundaries survive does a stochastic planner → implementer →
tester → reviewer workflow become worth the model and token cost.

## OpenLine placement

RCDL remains an ACE backend between trace capture and enforcement:

- OpenTelemetry supplies structured traces;
- ACE proposes and attacks clauses;
- external behavior and interventions decide standing;
- Claim Graph remembers why standing persists or falls;
- Receipt Gate may consume a frozen contract only after independent policy
  verification.

The RCDL-004 projection has authorization `NONE`. It is evidence, not a green
check and not permission to enforce anything.

## Final takeaway

RCDL-004 killed the flattering version of the claim.

The frozen contracts were perfect predictors, but a learned relational model
was also perfect. The remaining value is not “we alone can predict failure.” It
is the possibility of a machine-discovered, intervention-tested account of
which relationships actually matter, why they matter, and how recovery should
work.

That is narrower, harder, and more worth testing.

