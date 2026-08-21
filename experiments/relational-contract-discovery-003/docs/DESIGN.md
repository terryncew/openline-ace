# RCDL-003 design boundary

## Frozen claim

The frozen RCDL-002 contract family should predict external failure and bounded
recovery in a separately written deterministic repair workflow without changing
the RCDL 0.1 engine or clause bytes.

## Independence that is actually tested

`rcdl003/replica.py` is a new event-journal implementation. It does not import
or call `rcdl002`. CI places only RCDL-001 and RCDL-003 on `PYTHONPATH`, then
asserts that `rcdl002` is not importable before loading the replica.

This establishes code-path separation. It does not establish independence of
the developer, institution, repository, experimental design, or oracle. Those
remain shared causes and explicit blockers.

## Leakage boundary

The independent trace contains no hook name, active/sham arm, oracle result, or
failure label. Mutation markers carry only structural energy. The oracle reads
terminal ledger facts, not trace events. Ordinary predictive baselines remove
IDs, hashes, and direct intervention fields before fitting.

## Matched interventions

Each active/sham pair has exactly one mutation marker and the same event count.
The active arm changes a relation; the sham retains that relation and replaces
the displaced operation with padding or a safe terminal event. This controls
structural event count, not tokens, wall-clock latency, or semantic shock.

## Tournament

Training contains only single-fault active/sham examples. Held-out evaluation
contains two-, three-, and four-fault batches, plus the spurious-only control,
under five representation variants. RCDL receives no RCDL-003 training labels;
its predictor is the frozen four-clause family. Ordinary baselines receive
source labels, target-domain labels, or both as declared in the manifest.

The strict-win rule is:

1. higher held-out balanced accuracy than the best declared baseline; and
2. failure-class F1 no worse than that baseline.

No p-value is reported because deterministic seeds are not independent random
samples. Repetition tests implementation stability, not population inference.

## Scientific failure modes

The experiment fails if any target does not reproduce, the spurious clause is
promoted, a sham fails, event counts differ, nuisance transforms change RCDL
evaluation, a proper subset preserves all target scenarios, source code is
imported at runtime, or the manifest overstates independence or authority.

A valid but unfavorable baseline result is not a software failure. It is
recorded as `RCDL_PARITY` or `RCDL_NOT_BEST` while CI remains green if the
evidence is internally valid.
