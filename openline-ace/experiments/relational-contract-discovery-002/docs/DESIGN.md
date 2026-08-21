# RCDL-002 design boundary

## External behavior

"Same system" means that the workflow makes the correct release decision,
releases only an artifact that passes hidden tests and authorized-side-effect
checks, relies on test and review evidence for that artifact, never approves a
known failing test result, and recovers within the declared horizon when
recovery is available.

These properties live in a `WorkflowOutcome` object that is not serialized
into the discovery trace. The oracle does not import the clause evaluator or
candidate catalogue.

## Intervention scenarios

| Hook | Active mutation | Guarded sham behavior | External failure |
|---|---|---|---|
| `test_evidence_guard` | A stale passing run is relabeled as evidence for the current broken patch. | The identity mismatch is quarantined. | Broken artifact release and stale evidence. |
| `review_patch_guard` | A stale inspection is accepted for the current unsafe patch. | The mismatch is quarantined. | Unauthorized side effect. |
| `approval_test_guard` | A patch with a current failing test result is approved. | The patch is rejected. | Incorrect release decision and hidden-test failure. |
| `recovery_observation_guard` | Fresh observation is delayed beyond the three-step horizon. | Fresh observation occurs immediately. | Recovery deadline miss. |
| `planner_review_note_guard` | The stable planner note is omitted. | The note is emitted. | None; this clause must be rejected. |

Every arm records one intervention event with energy 1. In this deterministic
substrate that matches structural mutation count. It is not evidence that
token, latency, or semantic shock are matched for LLM workflows.

## Success criteria

- all five candidates are mined from successful traces;
- all four target clauses fail under their active mutation and coincide with
  independent oracle failure;
- all shams preserve the clause and oracle;
- the planted note clause fails under removal while the oracle stays passing;
- decisions survive actor renaming, event-ID renumbering, JSON-key reordering,
  held-out task seeds, and OTLP round trips;
- exhaustive reduction returns one inclusion-minimal four-clause family; and
- the frozen RCDL-001 engine digests remain unchanged.

## Falsifiers

The calibration fails if any target has active/sham parity, the spurious note
is promoted, oracle labels enter the trace, nuisance transforms change clause
evaluation, a proper subset preserves every scenario, recovery exceeds its
horizon, or the experiment requires a change to RCDL 0.1 semantics.
