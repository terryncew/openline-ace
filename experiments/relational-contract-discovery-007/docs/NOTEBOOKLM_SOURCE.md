# RCDL-007 study source: before the verdict exists

## Executive summary

RCDL-007 asks the question left open by the previous pressure tests: perhaps a
symbolic relational representation is not better at classifying evidence once
causal statistics have already been computed, but is better at deciding which
evidence to acquire next.

The experiment removes the most important shortcut from RCDL-006. Evaluation
policies do not receive artifact validity, hidden causal labels, relation names,
recovery horizons, or verdict-derived features. They see the same passive raw
observation, the same opaque probe menu, and the same raw probe outcomes. Each
has a four-query budget.

The learned baseline is not starved. Its development history is action-complete:
all ten probe outcomes are available for every development family, together
with development standing labels. Both policies use the same deterministic
minimax active-search rule.

The result remains parity.

Symbolic RCDL and the learned active baseline each score 320/320, use 544 probes
total, average 1.7 probes, never use more than two, and transport across two
separate execution adapters. A 4,096-sample nuisance probe finds zero policy
mismatches.

The frozen verdict is `PRE_ADJUDICATION_CAUSAL_PARITY` and the claim effect is
`UNIQUE_PRE_ADJUDICATION_UTILITY_NOT_FOUND`.

## The design lesson

RCDL-004 showed learned predictive parity. RCDL-005 showed learned causal-utility
parity when historical intervention signatures were action-complete. RCDL-006
held out entire mechanism compositions but still supplied a compact causal
signature that included verifier-derived artifact validity. RCDL-007 removes
that feature and moves the contest before final causal adjudication.

The learned policy still ties.

That narrows the useful claim. The explicit relational model may be easier to
audit or govern, but this synthetic program no longer supports saying that it
has unique causal-search utility merely because it is symbolic.

## What each side knows

The symbolic policy knows a compositional hypothesis grammar: four possible
fault relations and how each opaque intervention partitions the hypothesis
space. It does not know the hidden scenario.

The learned policy does not receive the relation identities. It stores complete
development response signatures over the same opaque probes plus development
standing labels. At evaluation it keeps the nearest response signatures under
the observations seen so far and uses the same minimax rule to choose the next
probe.

This isolates the proposed advantage to representation rather than giving the
symbolic policy a larger action budget or a better probe selector.

## Why the result matters

A symbolic system can look special when the learned competitor is forced to
predict from incomplete historical signatures or when the benchmark hands both
systems a precomputed causal verdict. RCDL-007 removes both excuses inside the
pilot.

The learner does not need to recreate the symbolic ontology explicitly. With
complete primitive intervention experience, its response signatures are enough
to make the same active decisions on unseen compositions.

That is the important negative result.

## What remains alive

Three narrower uses remain plausible without contradicting this result:

1. symbolic contracts as auditable explanations;
2. symbolic clauses as portable governance objects;
3. explicit relational hypotheses when historical intervention coverage is
   sparse or costly.

The third is a reopening condition, not a current finding. Testing it would
require a genuinely different evidence regime, preferably external rather than
another synthetic same-builder tournament.

## Authority

None. This is ACE Level 1 experimental evidence. It cannot authorize live
actions or policy changes.
