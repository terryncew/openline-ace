# RCDL-007 frozen protocol

Status: frozen after implementation audit and before repository publication  
Experiment: `relational-contract-discovery-007`  
Authority: `NONE`

## Falsifiable question

When post-adjudication features are removed, does an explicit relational
hypothesis space let RCDL reach the correct causal standing with fewer counted
probes than a strong learned active baseline under the same observation and
query budget?

The unique-advantage claim survives only if symbolic RCDL matches or exceeds
standing accuracy and uses at least 20% fewer counted probes.

## Why this experiment exists

RCDL-006 held out mechanism implementations and compositions, but both policies
classified a five-field signature that included `active.artifact_valid`. That
field was produced by the original verifier and almost directly separated
native from wrapper-imposed failure. The public policy-boundary metadata also
omitted `artifact_valid` from its learned-input list even though the learned
policy consumed the full signature.

RCDL-007 does not rewrite or reinterpret the frozen RCDL-006 result. It changes
the question. Evaluation policies must choose evidence before causal standing
is revealed.

## Hidden causal arena

The arena contains four possible causal faults:

- two native relations: freshness and lineage;
- two imposed relations: submit gate and timeout gate.

A hidden scenario is a subset of those faults. Standing is determined only for
scoring:

- no causal fault -> `NUISANCE`;
- only native faults -> `NATIVE`;
- only imposed faults -> `IMPOSED`;
- both kinds -> `MIXED`.

The policy never receives the hidden fault set.

## Public intervention surface

There are ten opaque probes, `probe-00` through `probe-09`. Internally they
repair one- or two-relation subsets. The symbolic policy has an explicit
hypothesis model that predicts each probe outcome. The learned policy receives
only action-complete development response signatures keyed by the opaque probe
IDs.

A probe returns `RawObservation`:

- `external_success`;
- `event_count_bucket`;
- `surface_tag`.

The latter two are nuisance fields varied by scenario identity, seed, and
adapter. Neither policy receives `artifact_valid`, a hidden fault set, standing,
recovery horizon, relation names, or verdict-derived features at evaluation.

A passive raw observation is free. Each selected probe costs one query. The hard
budget is four queries.

## Development and evaluation split

Development contains seven causal families:

- nuisance/no fault;
- each of the four single faults;
- two crossed mixed pairs.

The learned baseline receives the complete ten-probe response signature and the
training standing for every development family.

Evaluation contains ten families:

- a new nuisance identity family;
- the held-out dual-native composition;
- the held-out dual-imposed composition;
- the two crossed mixed pairs absent from development;
- all four triple-fault compositions;
- the four-fault composition.

Every non-nuisance evaluation fault set is absent from development.

## Policies

### Symbolic RCDL

The symbolic policy starts with the complete 16-hypothesis relational version
space. It filters hypotheses after the passive observation and each selected
probe. At each step it selects the unqueried probe that minimizes the worst-case
number of remaining standing classes, then remaining hypothesis count, then
partition imbalance.

### Learned active baseline

The learned baseline stores the action-complete development response signatures
and development standing labels. At evaluation it computes the development
records with minimum Hamming disagreement against the observations seen so far.
It uses the same deterministic minimax partition rule over those nearest learned
records to choose the next opaque probe. It receives no hidden relation identity
or evaluation standing.

This is deliberately favorable to the learner: development is action-complete
and the active-selection algorithm is shared.

## Independent adapters

Every evaluation scenario is executed through two separate code paths:

- `ledger-v3` collects unrepaired faults in a ledger;
- `queue-v3` drains faults through a queue.

They must agree on `external_success` while producing different nuisance
surface tags. Policy standing and probe sequence must transport across both.

## Endpoints and stop rule

Primary endpoint: exact standing accuracy.  
Secondary endpoint: total counted probes.

A unique symbolic query-efficiency advantage requires:

1. symbolic accuracy >= learned accuracy; and
2. symbolic total probes <= 80% of learned total probes.

If accuracy and query cost tie, the verdict is
`PRE_ADJUDICATION_CAUSAL_PARITY` and the synthetic unique-advantage claim is
retired.

## Frozen result

Evaluation emits 640 canonical rows:

- 10 evaluation families;
- 16 identities per family;
- 2 independent adapters;
- 2 policies.

Per policy:

- 320/320 correct;
- 1,000,000 ppm accuracy;
- 544 counted probes;
- mean 1.7 probes;
- maximum 2 probes.

Transport failures: zero.  
Randomized nuisance comparisons: 4,096, zero mismatches.

Scientific verdict: `PRE_ADJUDICATION_CAUSAL_PARITY`.  
Claim effect: `UNIQUE_PRE_ADJUDICATION_UTILITY_NOT_FOUND`.

## Interpretation boundary

The result says that, in this deterministic compositional arena, removing the
RCDL-006 post-adjudication feature did not uncover a symbolic advantage. An
action-complete learned signature policy selected the same probes, reached the
same standings, and paid the same query cost.

It does not prove symbolic contracts are useless. They may remain preferable
for auditability, explanation, governance, or explicit hypothesis custody. It
also does not establish parity for stochastic LLM agents, real software systems,
open-ended probe generation, sparse historical data, or independently designed
testbeds.

Those are different claims. This experiment closes the synthetic
unique-causal-search-advantage claim rather than automatically opening another
benchmark.

## Reopening conditions

Reopen only if a materially different regime supplies evidence that the learned
baseline lacks while preserving equal information and action budgets, such as:

- sparse rather than action-complete historical intervention coverage;
- stochastic agents with repeated trials and confidence bounds;
- externally generated causal topologies;
- a real verifier where probe cost is consequential;
- independent replication that breaks the parity result.

No enforcement or policy authority is granted by this experiment.
