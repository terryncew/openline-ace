# Relational Contract Discovery: Current State After RCDL-005

## Executive answer

Relational Contract Discovery, or RCDL, is an engineering instrument for
proposing relational rules from traces and attempting to falsify them with
controlled interventions. It is not a theory of everything and it does not
measure a mystical scalar called coherence. Its target is narrower:

> discover a family of inclusion-minimal relational contracts that preserves a
> predeclared external behavior under a defined perturbation regime.

RCDL-005 tested whether explicit symbolic contracts retain a unique practical
advantage once a learned policy has access to a complete library of historical
intervention outcomes. The answer in this deterministic calibration was no.
The symbolic and learned policies tied exactly. This is a successful
falsification milestone because it narrows the research claim and prevents the
project from treating relational vocabulary as automatically superior.

## Where the idea came from

The motivating intuition was that a system may be better characterized by
relationships it must preserve than by a single health or coherence score.
Neighboring formal traditions already include behavioral equivalence,
bisimulation, computational mechanics, assume/guarantee contracts, causal
representation learning, fault injection, and invariant mining. The project’s
possible contribution is therefore not a new metaphysics. It is an automated
instrument that discovers bounded candidate clauses, attacks each clause with
matched controls, measures recovery, prunes non-minimal explanations, and
records exactly why a surviving rule still has standing.

The key correction was to replace “the smallest set that makes a system remain
itself” with a testable object. “Identity” is defined by an independently
observable external contract: tests, safety properties, authorized side
effects, outputs, or latency. There may also be several sparse mechanisms that
implement the same behavior, so the output is a family of inclusion-minimal
contracts rather than one privileged invariant set.

## What the first four experiments established

RCDL-001 built the deterministic Raft calibration. It established a bounded
clause grammar, targeted interventions, matched shams, an official oracle,
minimality checks, and evidence manifests. Raft supplied known safety and
liveness relationships, cheap fault injection, and deterministic ground truth.

RCDL-002 transported the frozen engine into a deterministic planner to
implementer to tester to reviewer workflow. It tested patch provenance, current
review evidence, approval ordering, recovery from fresh observations, and a
spurious planner-note correlation. This remained a deterministic state-machine
calibration, not an LLM experiment.

RCDL-003 reimplemented the workflow through an independent queue/ledger code
path and added a baseline tournament. It checked that the claimed relationships
were not artifacts of a single implementation and explicitly tested recovery
horizons and nuisance changes.

RCDL-004 then applied learned relational baselines to 1,824 frozen examples,
including 1,024 final-audit traces. A learned high-precision relational DNF
matched the frozen RCDL predictor exactly. Both reached 480 true positives, 544
true negatives, and zero errors on the final audit. The correct conclusion was
that unique predictive superiority had been falsified within that tournament.
The remaining possible opening was causal utility: perhaps contracts were still
better for selecting interventions, explaining failures, or predicting
recovery.

## What RCDL-005 built

RCDL-005 is the Budgeted Causal Utility Tournament. It compares two active
policies under an equal-information and equal-action protocol.

The symbolic RCDL policy starts with a bounded version space of candidate
contract families. The learned policy starts from a frozen table of historical
active/sham outcomes. That table contains one opaque context for each candidate
mechanism and every allowed action, but no hypothesis names, behavioral-class
labels, or final scenario identities. The learned policy clusters identical
outcome signatures. Both policies then use the same minimax rule to choose the
next intervention.

The substrate has four abstract relations: provenance, review, ordering, and
fresh state. The action vocabulary contains ten interventions that break one or
two relations. Each active intervention has a matched sham with the same
declared abstract energy. The official oracle judges only external behavior.
When an active intervention fails, the policy selects a relation to restore and
the harness measures immediate and eventual recovery.

There are nine structural mechanisms but only eight observable classes in the
declared action regime. Two mechanisms are deliberately identical under every
single- and double-relation intervention but differ under excluded triple
breaks. A valid instrument must say `NON_IDENTIFIABLE`; choosing either hidden
mechanism would be overclaiming.

The final audit contains 256 held-out scenario identities, balanced at 32 per
observable class. Every scenario is executed through two adapters, `ledger` and
`queue`, and tested by both policies. This yields 1,024 policy/implementation
records. Each policy may use at most four active interventions.

## Result

The scientific verdict is `CAUSAL_UTILITY_PARITY`.

Both policies:

- recovered 512 of 512 implementation-level behavioral contracts;
- correctly classified structural identifiability 512 of 512 times;
- used exactly 1,536 queries, or three per run;
- achieved 704 immediate recoveries in 768 failure episodes;
- achieved 768 eventual recoveries in 768 failure episodes;
- produced zero sham failures;
- transported without decision changes across both implementations;
- remained stable across declared nuisance variants.

The receipt claim is therefore not “RCDL wins.” It is:

`UNIQUE_CAUSAL_UTILITY_FALSIFIED_WITHIN_TOURNAMENT`.

This means explicit symbolic contracts showed no unique causal-selection,
recovery, or normalized-explanation advantage when the learned baseline already
had an action-complete intervention-signature library. It does not mean
contracts are useless. The two policies recovered the same behavioral object
through different representations. The result says that representation alone
did not create an advantage in this regime.

## Why this is still a useful build

The harness now contains machinery the project previously lacked: equal-budget
active policies, a deterministic exhaustive oracle, intervention/sham pairing,
recovery decisions, correct non-identifiability, implementation transport,
canonical result records, fail-closed manifests, a bounded handoff projection,
source/evidence digests, deterministic replay, isolated-copy testing, randomized
nuisance probes, and CI across supported Python versions.

It also demonstrates the governing principle of ACE: a discoverer may propose
a rule, but it cannot declare its own rule true. The external oracle and frozen
verdict logic decide what survives. A green CI check means that the recorded
experiment is reproducible and internally consistent. It does not mean that a
broad scientific hypothesis is true.

## Limitations that must travel with the result

The same builder designed both policies, the substrate, and the harness. The
protocol was internally frozen before the committed evidence package but was
not externally preregistered. The learned history is action-complete and thus
favorable to the learned baseline. The symbolic policy receives a domain-supplied
grammar. The two adapters are independent render/parse paths but share one
official behavioral oracle. The perturbation regime excludes triple and
four-relation breaks. There are no stochastic models, prompts, tokens, tool
failures, timing effects, hidden software tasks, or live side effects. Nothing
in RCDL-005 authorizes enforcement or automatic promotion.

## What should be built next

The next honest experiment is not another synthetic variant tuned by the same
builder. RCDL-006 should be a genuinely mechanism-held-out tournament. The
learned policy must train on some causal mechanisms and encounter new contract
compositions at final audit. The symbolic grammar must also be frozen before
those mechanisms are generated. An external generator or independent
implementer should own the hidden mechanisms and oracle. This tests whether the
symbolic relational prior improves compositional transport when historical
signatures are incomplete.

Only if RCDL survives that test should the project move to a deterministic
compiler/linter repair loop, followed later by a stochastic planner to
implementer to tester to reviewer workflow. The first LLM claim must freeze
tasks, prompts, model versions, tool interfaces, perturbations, sham matching,
external tests, and stop rules. It must compare against learned active policies,
ordinary trace classifiers, latency/token baselines, graph statistics, and
full-trace models.

The present stopping rule is clear: predictive superiority is already rejected
in RCDL-004, and unique causal utility is rejected in the action-complete
deterministic setting of RCDL-005. The only remaining scientific opening is
out-of-distribution compositional efficiency under genuinely held-out causal
mechanisms, followed by independent replication. If that fails, RCDL remains a
useful evidence and fault-injection format, not a privileged discovery theory.

## Verification commands

From `experiments/relational-contract-discovery-005`:

```bash
export PYTHONPATH="."
python3 -m unittest discover -s tests -v
python3 -m rcdl005 verify-domain
python3 -m rcdl005 verify-policy-boundary
python3 -m rcdl005 verify-oracle
python3 -m rcdl005 verify-evidence
python3 scripts/freeze_history.py --check
python3 scripts/randomized_probe.py --samples 512
python3 scripts/release_check.py
```

The verified handoff projection has policy authority `NONE`. Evidence and
policy must always be checked together; signatures alone are insufficient.

