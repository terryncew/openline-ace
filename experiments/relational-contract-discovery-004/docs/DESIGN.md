# RCDL-004 design

## Claim under test

RCDL-003 left open a broad predictive claim: perhaps intervention-tested
contracts predict unseen workflow failure better than a model trained only on
traces and outcome labels.

RCDL-004 gives that claim a stronger chance to fail. Learned models receive
generic relational representations, including equality joins that RCDL-003's
ordinary baselines were denied. A parity result rejects predictive uniqueness.
A valid unfavorable scientific result must remain a passing software result.

## Frozen corpus

The corpus contains 1,824 canonical traces:

- 640 single-fault training examples from seeds 0-63;
- 160 single-fault validation examples from seeds 1000-1015;
- 1,024 multi-fault final-audit examples from seeds 90000-90031.

The final audit covers 16 perturbation sets, active and sham arms, and five
representation variants. Direct arm, hook, target, and oracle labels are
absent from every trace. Labels exist beside traces for training and scoring.

The compressed corpus and decompressed payload have independent SHA-256
bindings. The manifest also binds the RCDL-003 generator source, clauses, and
the RCDL-0.1 engine reference.

## Generic relational representations

The sequence representation includes event n-grams, canonical actor roles,
safe scalar state, within-task ordering, and equality/inequality relations.
Identity-like values are erased. The graph representation adds temporal,
same-task, same-patch, and different-patch edges followed by two
Weisfeiler-Lehman relabeling rounds.

The task-bag models use raw task ids only to establish equality partitions.
The values never enter model features. Their declared structural prior is that
global failure occurs when any opaque task segment is predicted to fail.

## Model selection

Tree depth, leaf size, and perceptron epochs are chosen on validation data
only. The final relational DNF has a frozen support threshold of 32. Candidate
rules contain one or two generic features, must have zero observed negative
support, and must meet the support floor.

For each positive training example, the DNF retains all equally simple
minimum-cost explanations. This tie policy is crucial. An arbitrary single
tie-break learned a planner-note shortcut and failed a harmless planner-note
interaction. Keeping the equivalence class produced a 31-rule model that
transported to the sealed audit split.

## Verdict rule

Balanced accuracy is primary and failure-class F1 is the guard metric:

- `LEARNED_PARITY`: both primary metrics equal;
- `RCDL_STRICT_WIN`: RCDL has higher balanced accuracy and no worse F1;
- `LEARNED_STRICT_WIN`: the learned model has higher balanced accuracy and no
  worse F1;
- `MIXED_RESULT`: neither dominance rule holds.

The observed verdict is `LEARNED_PARITY`: both predictors scored 1,000,000 ppm
balanced accuracy and 1,000,000 ppm failure F1 on 1,024 examples.

## What parity changes

Rejected within this tournament:

> RCDL has a unique predictive advantage over learned relational trace models
> on the deterministic repair substrate.

Still outside this tournament:

- whether predictive models can identify interventionally necessary clauses;
- whether they select efficient falsifying interventions;
- whether their explanations remain stable under representation changes;
- whether either approach transports to stochastic LLM workflows.

RCDL therefore survives as a causal-discovery and verification instrument,
not as a uniquely accurate classifier.

