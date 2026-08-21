# Relational Contract Discovery: RCDL-003 study source

## The program in one sentence

Relational Contract Discovery is an instrument that proposes bounded rules
from successful traces, attacks them with targeted interventions and matched
shams, lets an external behavior oracle decide what broke, and retains only
inclusion-minimal clauses that transport.

It is not a coherence score and not a theory of everything.

## Where RCDL-003 sits

The calibration ladder now has three rungs:

1. **RCDL-001 — Raft micro-harness.** The engine rediscovered locally known
   safety relationships and rejected a planted observational rule.
2. **RCDL-002 — deterministic repair workflow.** The same engine, unchanged,
   found four necessary workflow relations and one bounded recovery relation.
3. **RCDL-003 — separate implementation and baseline tournament.** The engine
   and clauses are frozen, moved to a new queue-driven implementation, and
   compared with ordinary predictive alternatives.

The point of rung three is to test whether the earlier result was merely a
feature of the simulator that produced it.

## The frozen contract family

The four retained clauses are:

1. A passing test result must follow a test run for the same task, suite, and
   patch hash.
2. Approval must follow inspection of the same task and patch hash.
3. Approval must follow a passing required-suite result for the same patch.
4. A detected failure must be followed by a fresh workspace observation for
   the same recovery cycle within three logical steps.

A fifth rule says that a planner note must precede approval. It appears in all
successful source traces but is deliberately unnecessary. If RCDL-003 promotes
it, the causal-pruning claim fails.

## What “independent” means here

The RCDL-003 workflow has a distinct source file, execution path, state model,
actor names, artifact generator, event-ID scheme, and multi-fault batch model.
It cannot import the RCDL-002 runtime package under the declared environment.

That is code-path independence only. The same repository, research program,
builder, oracle design, and clause vocabulary remain shared. A favorable result
therefore cannot be called independent external replication.

This distinction matters because two implementations built by the same person
can share the same hidden assumption even when they share no code.

## The external identity contract

“The workflow remains itself” is replaced by explicit behavior properties:

- release only when release is expected;
- released patches pass hidden tests;
- released patches contain no forbidden side effect;
- test and review evidence refer to the released patch;
- approval rests on a passing required test; and
- recovery uses a fresh observation within its declared horizon.

The oracle reads terminal ledger facts. It does not read RCDL evaluations,
trace events, intervention arms, or baseline predictions.

## Active and sham arms

Each clause receives two arms.

The active arm severs the candidate relationship: it mismatches patch identity,
approves failing tests, approves after stale review, delays fresh observation,
or removes the planner note.

The sham arm preserves the relationship while applying a matched structural
change. Both arms have one unlabeled mutation marker and the same event count.
The trace does not say which hook was targeted or which arm ran.

This matching is deliberately narrow. Equal event count is not equal token
shock, wall-clock delay, or semantic disruption. Those controls belong to the
later stochastic experiment.

## The held-out test

Training examples contain one intervention at a time. Held-out examples combine
two, three, or four faults in the same trace. A spurious-only batch tests whether
the correlational planner-note rule causes a false alarm.

Every held-out trace cycles through five representation conditions:

- original representation;
- actor renaming;
- event-ID renumbering;
- object-key reordering; and
- OTLP conversion and normalization.

The frozen contract predictor declares failure when any of the four retained
clauses is violated. It receives no RCDL-003 training labels.

## The baseline tournament

The ordinary predictors are intentionally dependency-free and inspect only
trace features available at prediction time:

- a single scalar task/event-score decision stump;
- a nearest-centroid classifier over ordinary graph statistics;
- a Bernoulli classifier over event kinds, low-cardinality attributes, and
  adjacent event-kind pairs; and
- the full correlational temporal-rule set before intervention-based pruning.

The first three are tested both when trained on frozen RCDL-002 traces and when
adapted on RCDL-003 single-fault examples. Artifact identities, direct
intervention labels, and oracle values are excluded.

The temporal-rule baseline is important. It understands relational order, but
it lacks the active-vs-sham evidence needed to reject the planner-note rule.
That makes its false positive a direct measurement of what causal pruning adds.

These are bounded baselines, not the strongest imaginable models. A learned
sequence transformer, graph neural network, or classifier with generic
cross-event equality features could close the gap. RCDL-003 makes no claim
against models it did not run.

## How to read the result

`RCDL_STRICT_WIN` means the frozen contract predictor has higher held-out
balanced accuracy than every declared baseline and no worse failure-class F1.
It does not mean universal superiority.

`RCDL_PARITY` means at least one baseline matches both primary metrics.

`RCDL_NOT_BEST` means an ordinary baseline wins. That would be a valid
falsification result, not a broken harness.

The frozen evidence records a strict win inside the declared deterministic
matrix. The RCDL predictor is perfect on that matrix; the best ordinary control
is the unpruned temporal-invariant set, whose only errors come from treating the
planner-note correlation as necessary.

No significance claim is made. Deterministic seeds generate repeatable cases,
not independent samples from a population.

## What has standing now

The evidence supports this bounded statement:

> The frozen four-clause family transported to a separately written
> deterministic code path, predicted unseen multi-fault failure and recovery,
> and beat the declared bounded baselines while rejecting the planted
> correlational rule.

The standing is evidence-only. Receipt Gate may attach it but may not use it as
policy input. Claim Graph may remember the clause standing and its limitations.
Authorization remains `NONE`.

## What remains unproved

- independent developer or laboratory replication;
- open-ended automated rule synthesis;
- completeness of the clause vocabulary;
- superiority to strong learned sequence or graph baselines;
- transport across stochastic model or prompt changes;
- token-, timing-, and semantic-shock-matched interventions;
- live OpenTelemetry monitoring;
- safe automatic mutation of production workflows; and
- any general law of biological or social organization.

## The next discriminating test

Before an expensive LLM workflow, the cleanest pressure test is a stronger
baseline that can learn generic cross-event equality and sequence structure
without receiving the frozen clauses. If that model reaches parity, RCDL's
opening narrows from predictive advantage to causal legibility and
intervention efficiency. If RCDL still wins, the stochastic rung becomes worth
the cost.

External replication by another developer is orthogonal. It tests shared
assumptions rather than classifier strength. Both are required before any
promotion beyond ACE Level 1 Candidate.

## Questions for study

1. Why is a new code path weaker evidence than a new research team?
2. Why must a predictive baseline be denied intervention and oracle labels?
3. What does event-count matching control, and what does it leave open?
4. Why does the planner-note baseline reveal the value of causal pruning?
5. Why are deterministic seeds not a basis for a p-value?
6. What generic relational features could let a strong classifier tie RCDL?
7. Why can a valid scientific loss coexist with green CI?
8. What additional evidence would permit the projection to become policy input?

## One paragraph to remember

RCDL-003 does not prove a theory of organization. It takes a frozen relational
contract family from one deterministic repair simulator, runs it unchanged on
a separately written queue-driven implementation, attacks the clauses under
matched active and sham arms, tests unseen multi-fault combinations and harmless
representation changes, and compares failure prediction with ordinary trace
baselines. The family transports and wins this bounded tournament, chiefly
because intervention evidence rejects a spurious planner-note rule. The result
is real but local: same repository, same builder, no strong learned relational
baseline, no stochastic agents, and no enforcement authority.
