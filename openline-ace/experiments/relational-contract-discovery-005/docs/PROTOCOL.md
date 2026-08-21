# RCDL-005 Frozen Protocol

## Falsifiable question

Does a symbolic Relational Contract Discovery policy retain causal selection,
recovery, or explanation utility over a learned intervention-signature policy
when information and online action budgets are equal?

## Compared policies

`rcdl_symbolic_version_space` begins with eight outcome-distinct candidate
classes derived from the bounded relational contract grammar. It filters that
version space after each active intervention.

`learned_intervention_signature` receives the frozen historical table: ten
active/sham outcomes for each of nine opaque candidate-mechanism contexts. It
clusters identical signatures into eight outcome classes. It never receives
hypothesis IDs, class labels, final scenario IDs, or direct oracle access.

Both policies choose the next intervention by the same deterministic minimax
partition rule. This intentionally isolates representation of prior knowledge:
explicit contract families versus learned causal outcome signatures.

## Contract object

A structural mechanism is an inclusion-minimal family of sufficient relation
sets. The official oracle preserves behavior when at least one sufficient set
remains intact. The declared intervention regime breaks one or two of four
relations. A behavioral contract is the complete ten-action failure signature
plus its inclusion-minimal failure sets.

Nine structural mechanisms produce eight behavioral classes. Two mechanisms
share the same ten-action signature but differ under excluded triple-relation
breaks. Correct output for that class is `NON_IDENTIFIABLE`, not an arbitrary
structural choice.

## Dual-arm intervention

Every query executes:

1. an active arm that severs the selected relation set;
2. a sham arm with the same declared abstract energy but only surface mutation;
3. an independent external behavior observation;
4. when the active arm fails, one policy-selected restoration followed by the
   official recovery observation.

A sham failure, unequal declared energy, exhausted version space, budget
violation, adapter disagreement, or unresolved output invalidates the
tournament.

## Audit matrix

The final audit contains 32 scenario identities per behavioral class, or 256
scenarios total. Each runs through both `ledger` and `queue` adapters and both
policies: 1,024 policy/implementation results. Nuisance seeds alter irrelevant
annotations and ordering. Normalized decisions and explanations must not change.

## Endpoints and verdict

The primary endpoint is exact behavioral-contract recovery within four active
queries. Secondary endpoints are query count, correct non-identifiability,
immediate/eventual recovery, transport, nuisance stability, and sham behavior.

The frozen verdict is `CAUSAL_UTILITY_PARITY`. Both policies achieved 512/512
correct implementation-level contracts, 512/512 structural-status decisions,
1,536 total queries (three per run), 704/768 immediate recoveries, 768/768
eventual recoveries, and zero sham failures.

The claim effect is
`UNIQUE_CAUSAL_UTILITY_FALSIFIED_WITHIN_TOURNAMENT`.

## Honest boundary

This protocol was internally frozen before the committed evidence package, but
it was not externally preregistered. The same builder designed both policies,
the mechanisms, and the harness. The learned history is action-complete, which
is a favorable and explicitly bounded setting. The adapters are independent
code paths but share one official oracle. No live agent or stochastic transport
was tested. The result grants no enforcement authority.

