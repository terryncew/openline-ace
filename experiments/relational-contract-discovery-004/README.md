# RCDL-004: learned relational baseline pressure test

RCDL-004 tests the nearest surviving falsifier from RCDL-003:

> Can a learned model with generic sequence, graph, and cross-event equality
> features match the frozen four-clause RCDL predictor on unseen multi-fault
> traces without receiving the clauses, intervention labels, hook names, or
> oracle values at prediction time?

The answer in this bounded deterministic tournament is **yes**.

Both the frozen RCDL predictor and the best learned baseline classified all
1,024 final-audit traces correctly. The scientific verdict is
`LEARNED_PARITY`. The broad claim that RCDL has a unique predictive advantage
on this substrate is therefore rejected.

That result does not erase RCDL-001 through RCDL-003. The learned baseline
predicts outcomes; it does not reproduce targeted interventions, matched
shams, recovery tests, causal pruning, or inclusion-minimal contract standing.
The surviving opening is causal legibility and intervention efficiency, not
predictive uniqueness.

## Information boundary

Learned models may use:

- 640 labeled training traces and 160 validation traces;
- event order and event kinds;
- actor structure after first-occurrence canonicalization;
- generic cross-event equality and inequality;
- opaque task-identity equality for multiple-instance aggregation.

They may not use:

- RCDL clause definitions;
- intervention arms, hook names, or targets;
- external-oracle values at prediction time;
- raw task ids, artifact hashes, run ids, or event ids as features;
- the 1,024 final-audit labels before scoring.

## Models

The tournament includes deterministic relational decision trees, a two-round
Weisfeiler-Lehman event-graph tree, a sparse margin model, a task-bag tree, and
a minimum-description relational DNF. The DNF retains every equally simple,
zero-observed-false-positive explanation instead of choosing a lucky lexical
shortcut. It reaches parity with 31 one- or two-feature rules.

These are meaningful learned relational baselines, but they are bounded
standard-library models. No neural sequence model, graph neural network, or
external hyperparameter service is tested.

## Development disclosure

Seeds 30000-30031 were observed while the learned control was being hardened
and are excluded from final scoring. The final audit uses seeds 90000-90031,
selected after the model and tie policy were frozen.

This is still weak independence: seed changes alter opaque identities, not the
deterministic fault semantics. The same builder designed the workflow, models,
and audit. No significance claim or external-replication claim is made.

## Run

```bash
cd experiments/relational-contract-discovery-004
export PYTHONPATH=../relational-contract-discovery-001:.
python -m unittest discover -s tests -v
python -m rcdl004 verify-bindings
python -m rcdl004 run --output pressure-test-out
python -m rcdl004 verify-manifest pressure-test-out/pressure-test-manifest.json
python -m rcdl004 verify-projection pressure-test-out/contract-projection.json
```

Corpus regeneration is an explicit provenance check and is the only step that
imports the RCDL-003 generator:

```bash
PYTHONPATH=../relational-contract-discovery-001:../relational-contract-discovery-003:. \
  python scripts/freeze_corpus.py --check
```

## Authority

The projection is evidence-only. Receipt Gate may attach it but may not use it
as policy input. Authorization remains `NONE`.

