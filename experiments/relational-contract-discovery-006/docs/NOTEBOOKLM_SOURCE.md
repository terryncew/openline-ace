# RCDL-006 study source: EnvHarness, held-out mechanisms, and the authority boundary

## Executive summary

Relational Contract Discovery (RCDL) is a falsifiable engineering program for
discovering candidate relationships and trying to break them. Its object is not
“the essence of a system.” Its object is a family of inclusion-minimal
relational contracts that preserve a predeclared external behavior under a
defined perturbation regime.

RCDL-006 asks a new question: can the instrument tell the difference between a
relationship the original behavior really needs and a requirement created by
the perturbation wrapper itself?

The experiment uses Google's EnvHarness core as the wrapper substrate.
EnvHarness is useful because it turns environments into programmable
intervention surfaces while retaining the original environment and verifier.
Its broader EnvRigger loop can observe behavior, propose wrappers, and validate
new rollouts. That is close to the intervention-proxy layer RCDL needed.

The crucial restriction is authority separation:

> EnvHarness may enact a mechanism. EnvRigger may propose one. Neither may
> decide that the mechanism is independently necessary.

Only the original verifier judges external success.

The frozen pilot result is `HELD_OUT_MECHANISM_CAUSAL_PARITY`. Symbolic RCDL and
an equal-budget learned signature baseline both correctly separated native,
wrapper-imposed, and nuisance mechanisms across unseen compositions and two
held-out agent implementations. RCDL crossed the “wrapper can manufacture a
rule” boundary in this toy substrate, but it did not show a unique advantage
over the learned baseline.

## The origin of the research program

The starting intuition was that persistent organization may be relational:
provenance, ordering, state dependence, information barriers, recovery, and
substitution may matter more than a single scalar “coherence” score.

That intuition is not a license for a theory of everything. Neighboring fields
already include computational mechanics, bisimulation, causal representation
learning, temporal invariant mining, assume/guarantee contracts, mechanistic
interpretability, and research that describes computation using persistent
relational constraints and recovery.

The potentially useful contribution is therefore an instrument:

1. capture execution traces;
2. propose bounded relational clauses;
3. make targeted interventions;
4. compare each intervention with a matched sham;
5. restore the relation and measure recovery;
6. test held-out transport;
7. prune clauses that are unnecessary or representation-dependent;
8. preserve claims, evidence, limitations, and reopening conditions in a
   verifiable handoff.

The discoverer proposes. It never certifies itself.

## Why “the system remains itself” was rejected

“Remains itself” is too elastic to falsify. RCDL instead declares an external
behavior before intervention. Examples include hidden tests, safety properties,
authorized side effects, output bounds, or latency limits.

Internal implementations may differ while remaining behaviorally equivalent.
There may also be several distinct minimal mechanisms because systems can use
redundancy or substitutes. The desired output is therefore a family of
inclusion-minimal contracts, not one privileged invariant set.

## The bounded clause grammar

An unrestricted logic miner can produce tautologies or explode
combinatorially. RCDL confines proposals to four primitive families:

- **Provenance:** an artifact or event must derive from a particular prior
  artifact or event.
- **State conditioning:** an action must condition on a fresh observation, not
  stale latent context.
- **Ordering and exclusion:** one action must precede another without a
  forbidden intervening mutation.
- **Information barriers:** a channel must not expose protected state before an
  allowed phase.

The pilot clause in RCDL-006 is a provenance-and-freshness claim:

> Successful submission requires fresh test evidence bound to the current
> patch hash.

## Why matched shams are essential

A targeted mutation can fail for uninteresting reasons: changed length,
latency, tokenization, formatting, field order, or a generic blocked-action
shock. A causal claim therefore needs a control with similar perturbation
energy that leaves the candidate relation intact.

RCDL-006 executes three arms for every case:

1. an active mechanism;
2. a matched sham;
3. a restoration arm.

A candidate has standing only when active and sham outcomes differ in the
declared causal way, restoration succeeds within a defined horizon, and the
result transports.

## What EnvHarness contributes

EnvHarness defines a common `ActionableEnv` interface and composable harnesses.
Its `Rules` wrapper exposes action, transition, and observation hooks. The
wrapper can block an action, transform a transition, or alter what an agent
observes while delegating evaluation to the inner environment.

RCDL-006 imports the actual upstream core from the official repository and
pins commit `fab7d57441f06b75c73a900e04561d4d7600f361`. Five source files are
bound by SHA-256. CI checks out that exact commit independently.

Official sources:

- paper: https://arxiv.org/abs/2608.19880
- repository: https://github.com/google-research/envharness
- project: https://envharness.com/

EnvHarness supplies the intervention machinery. It does not supply truth.

## The manufactured-rule problem

Suppose a wrapper blocks `submit` until `run_tests` has occurred. A correct
patch submitted without a test now “fails” at the wrapper boundary. If the
instrument looked only at wrapper-visible success, it could conclude that
tests-before-submission is necessary.

But remove the wrapper and ask the original verifier: the correct patch passes.
The rule was imposed by scaffolding.

This produces the central diagnostic distinction:

| Active outcome | Artifact validity | Interpretation |
| --- | --- | --- |
| External failure | Invalid artifact | Native verifier-relevant break |
| External failure | Valid artifact | Wrapper-imposed failure |
| External success | Valid artifact | Nuisance-invariant change |

Restoration then tests whether the proposed relation predicts recovery instead
of merely describing a symptom after failure.

## The code-repair pilot environment

Each task has a correct patch and an alternate patch. The original verifier is
deliberately small: success requires a submission and the correct current
patch. It never checks whether tests ran.

Native mechanisms corrupt the first test observation. An agent can then submit
the wrong patch, causing the original verifier to fail and the artifact to be
invalid.

Wrapper-imposed mechanisms start with a correct patch but block, shadow, or
time out a direct submission until a fresh test exists. The external run fails
while the artifact remains valid.

Nuisance mechanisms change role spelling, field presentation, order, or
padding. Behavior remains preserved.

## Development and held-out mechanisms

The development set has six single-layer mechanisms: two native, two imposed,
and two nuisance. The evaluation set has six two-layer compositions built from
an entirely disjoint operator vocabulary.

Holding out entire mechanisms matters. Holding out only task IDs while reusing
the same intervention semantics would test memorization of a mechanism under a
new label, not transport.

The final audit also uses sixteen new task identities and two held-out agent
implementations. One uses an explicit ledger; the other uses a queue. Agreement
must survive both control-flow paths.

## The competing policies

Both policies receive the same three-query transcript:

`(active success, active artifact valid, sham success, restoration success, recovery horizon)`

The symbolic policy uses the declared causal rule. The learned baseline builds
a lookup table from development signatures and official labels. It receives no
mechanism names, proposal IDs, clause parser, wrapper source, or oracle at final
prediction time.

The budget is equal: three queries per case for both policies.

## The result

Final evaluation contains 384 canonical result records:

- 16 held-out tasks;
- 6 held-out mechanism compositions;
- 2 held-out agent implementations;
- 2 competing policies.

Per policy:

| Standing | Correct decisions |
| --- | ---: |
| Native verifier-relevant | 64 / 64 |
| Wrapper-imposed | 64 / 64 |
| Nuisance | 64 / 64 |
| Total | 192 / 192 |

Both policies predicted all 192 recovery horizons. All matched shams preserved
external behavior. Agent transport passed. The accuracy difference was zero.

Scientific verdict: `HELD_OUT_MECHANISM_CAUSAL_PARITY`.

Claim effect:
`NATIVE_VS_IMPOSED_DISTINCTION_SUPPORTED_UNIQUE_ADVANTAGE_NOT_FOUND`.

## What the result proves inside the pilot

The executable harness can distinguish a verifier-relevant artifact failure
from a failure manufactured by a wrapper. It does so on mechanism operators and
compositions absent from development. Restoration and agent transport are
checked, not assumed. Evidence is digest-bound and fail-closed.

## What the result does not prove

It does not prove that RCDL is uniquely useful. The learned baseline ties it.
It does not prove that the clause exists in real software ecosystems. It does
not test live EnvRigger generation, arbitrary generated Python, LLM agents,
prompt variation, model swaps, real SWE-bench tasks, independent teams, or
external preregistration.

The builder wrote the environment, operators, policies, and tests. Determinism
makes replay exact; it does not create population-level statistical evidence.

## The relationship to earlier RCDL experiments

- **RCDL-001:** deterministic Raft calibration with known invariants.
- **RCDL-002:** transport to a deterministic planner-to-reviewer repair loop.
- **RCDL-003:** independent code path and bounded baseline tournament.
- **RCDL-004:** a learned relational model reached predictive parity.
- **RCDL-005:** an action-complete learned policy reached causal-utility parity
  in the historical deterministic tournament.
- **RCDL-006:** real EnvHarness core, held-out mechanism compositions, and an
  explicit test for rules manufactured by wrappers; parity remains.

The program has become stricter as its positive claims have narrowed. That is
the intended behavior of a falsifiable engineering program.

## Evidence and accountability

The frozen package contains:

- canonical result JSONL;
- a manifest bound to the result digest;
- a verified handoff projection bound to the manifest;
- a release check from an isolated copy;
- randomized nuisance and transport comparisons;
- an experiment receipt;
- a closed evidence index with size and SHA-256 for every evidence file.

Every projection says policy authority `NONE`. Signatures and hashes establish
integrity, not truth or authorization. Evidence plus policy must be verified.

## What should be built next

RCDL-007 should introduce a genuinely independent mechanism source. A credible
next step would freeze an external set of EnvHarness/EnvRigger mechanisms before
the RCDL team sees their implementation, then evaluate on a separate verifier
and stochastic agents. The proposer must remain untrusted, and original
verifier outcomes must remain the oracle.

Useful escalation criteria include:

- mechanisms supplied by a separate builder;
- live EnvRigger proposals sandboxed and frozen before evaluation;
- unseen repositories and original test suites;
- at least one held-out model backend;
- prompt and formatting nuisance transformations;
- artifact-provenance corruption and restoration;
- baseline training under the same observation and intervention budget;
- externally archived preregistration and evidence.

Another same-builder synthetic composition would add little.

## Study questions

1. Why can a wrapper-generated failure not establish an independent contract?
2. Why is artifact validity needed in addition to run success?
3. What does a matched sham control for?
4. Why are whole mechanisms held out instead of only task identities?
5. What information is hidden from both policies?
6. Why is a learned tie scientifically important?
7. What does deterministic replay establish, and what does it not establish?
8. Which evidence fields prevent a receipt from becoming policy authority?
9. What would an independent RCDL-007 need to change?

## Glossary

**Candidate clause:** a proposed relationship that has not yet earned standing.

**External verifier:** the independently declared behavior evaluator.

**Native mechanism:** a perturbation that changes the artifact or behavior the
original verifier independently evaluates.

**Wrapper-imposed mechanism:** a requirement created by intervention
scaffolding rather than by the original verifier.

**Nuisance mechanism:** a representation change intended to preserve semantics.

**Restoration horizon:** the number of frozen recovery actions needed after a
targeted break.

**Transport:** preservation of the decision across held-out tasks,
implementations, mechanisms, or models.

**Causal-utility parity:** both policies make equally correct intervention and
recovery decisions under the declared budget.

**Authority `NONE`:** evidence may inform a decision but cannot authorize a
deployment, merge, promotion, or live action.
