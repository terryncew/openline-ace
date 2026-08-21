# RCDL-003: independent-code-path replication and baseline tournament

RCDL-003 asks the next bounded question in the calibration ladder:

> Do the frozen RCDL 0.1 engine and four RCDL-002 workflow clauses predict
> failure and recovery in a separately written deterministic implementation,
> and do they beat declared ordinary trace baselines on unseen fault
> combinations?

The answer recorded by the frozen evidence is **yes within this harness**. It
is not external replication and grants no enforcement authority.

## What changed

The source workflow in RCDL-002 is a direct scenario simulator. RCDL-003 uses a
new queue/ledger code path with different actors, event IDs, artifact
construction, batching, and control flow. It can execute multiple faults in one
trace. The implementation imports the frozen RCDL-001 engine but cannot import
`rcdl002`; the source implementation is present only for hash verification.

The following inputs are frozen byte-for-byte:

- the nine-file RCDL 0.1 engine;
- all five RCDL-002 clause files;
- ten representative RCDL-002 traces used by source-trained baselines; and
- the RCDL-002 workflow implementation digest.

## What is tested

For every clause, targeted active and matched sham arms use the same event
count and one unlabeled mutation marker. The trace does not expose the target,
arm, or oracle result. Four target clauses must fail behavior in the active arm
and preserve it in the sham. The planner-note rule must violate its clause
without changing external behavior.

The held-out tournament combines two, three, or four unseen faults and applies
actor renaming, event-ID renumbering, object-key reordering, and OTLP
round-trips. It compares the frozen four-clause predictor against:

- a scalar task/event-score stump;
- an ordinary graph-statistic centroid;
- a bag-of-symbols full-trace Bernoulli classifier; and
- temporal invariants without intervention-based causal pruning.

Both source-trained and target-adapted versions of the learned baselines are
included. Direct intervention labels, oracle values, and artifact-hash equality
features are unavailable to them.

## Run it

```bash
cd experiments/relational-contract-discovery-003
export PYTHONPATH="../relational-contract-discovery-001:."
python3 -m unittest discover -s tests -v
python3 -m rcdl003 verify-bindings
python3 -m rcdl003 verify-evidence
python3 -m rcdl003 run --output replication-out --trials 8
python3 -m rcdl003 verify-manifest replication-out/contract-manifest.json
python3 -m rcdl003 verify-projection replication-out/contract-projection.json
python3 scripts/randomized_probe.py --seeds 256
```

## Claim boundary

A passing result supports only deterministic transport across a separate code
path in the same repository. It does not establish:

- replication by an independent developer or laboratory;
- superiority to strong learned sequence or graph models;
- stochastic LLM-workflow transport;
- realistic token, wall-clock timing, or semantic-shock matching;
- open-ended clause discovery; or
- permission for Receipt Gate to enforce the discovered clauses.

The projection is evidence-only. Its authorization is always `NONE`.
