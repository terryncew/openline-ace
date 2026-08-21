# Relational Contract Discovery 002

This ACE experiment tests whether the frozen RCDL 0.1 engine transports from
the Raft calibration to a different deterministic domain: a rule-based
planner -> implementer -> tester -> reviewer repair workflow.

RCDL-002 does not use an LLM, a live OpenTelemetry collector, or a production
action gate. It isolates two questions that RCDL-001 could not answer:

1. Can the same clause grammar and evaluator identify necessary relationships
   in an agent-shaped workflow without modification?
2. Can a bounded progress clause predict recovery within a declared horizon?

## Frozen-engine boundary

The experiment imports `rcdl` directly from
`../relational-contract-discovery-001/`. It does not copy or modify the clause
parser, evaluator, miner, nuisance transforms, reducer, trace model, canonical
serializer, or OTLP adapter. `references/rcdl_0_1_engine_reference.json`
pins those files by SHA-256. A changed engine fails verification before the
calibration runs.

## Candidate contracts

- passing test evidence must derive from a run over the claimed patch;
- approval must follow inspection of the current patch;
- approval must follow a passing test result for the current patch;
- recovery after a detected failure requires a fresh workspace observation
  within three logical steps; and
- a planner-to-reviewer note is a planted observational control that must be
  proposed and rejected as causally irrelevant.

The independent oracle consumes a separate workflow outcome object. It checks
release correctness, hidden tests, authorized side effects, evidence
currentness, approval safety, and the recovery deadline. Oracle values are
never trace attributes and are unavailable to the candidate miner.

## Run

From this directory:

```bash
export PYTHONPATH="../relational-contract-discovery-001:."
python3 -m unittest discover -s tests -v
python3 -m rcdl002 verify-engine
python3 -m rcdl002 verify-evidence
python3 -m rcdl002 calibrate --output calibration-out --trials 8
python3 -m rcdl002 verify-manifest calibration-out/contract-manifest.json
python3 -m rcdl002 verify-projection calibration-out/contract-projection.json
python3 scripts/randomized_probe.py --seeds 64
```

No third-party Python package is required.

## Automation boundary

GitHub Actions reruns the tests, frozen-engine check, evidence verification,
fresh calibration, manifest/projection verification, and randomized probe on
every pull request or push that changes RCDL-001 or RCDL-002. You do not collect
traces by hand for this calibration: the deterministic harness generates them.

This is build-time experiment automation, not a continuously running production
monitor. It does not watch repositories, agents, or deployments after CI ends.
Live OpenTelemetry ingestion and enforcement remain deliberately out of scope.

For a single source suitable for NotebookLM, including the concept's lineage,
implemented experiments, falsifiers, vocabulary, and study questions, use
[`docs/NOTEBOOKLM_SOURCE.md`](docs/NOTEBOOKLM_SOURCE.md).

## Claim boundary

A pass supports only deterministic cross-domain reuse of the frozen RCDL 0.1
engine and local bounded recovery in this simulated workflow. It does not
establish open-ended rule discovery, transport to an independent workflow
implementation, realistic token/timing sham matching, stochastic LLM
transport, or permission to govern live actions.
