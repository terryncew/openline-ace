# HSR-001 — Healthcare Dependency Coverage Audit

This experiment asks a narrower question than "can Selective Reverification work in healthcare?"

> When a real clinical datum changes, does the exported record contain enough explicit dependency information to know which downstream standing should reopen?

That is a prerequisite for safe selective reopening. A perfect traversal algorithm can still falsely retain a downstream decision when the edge connecting that decision to changed evidence was never recorded.

## External arm: MIMIC-IV demo

HSR-001 freezes a small excerpt from the openly available, deidentified MIMIC-IV Clinical Database Demo v2.2. In one real hospitalization (`subject_id=10035631`, `hadm_id=21476294`), the dataset contains:

- a blood potassium result (`labevent_id=415122`, `itemid=50971`) at `2115-11-24 00:00:00`, value `3.7 mEq/L`;
- potassium-chloride replacement administrations in the same hospitalization on Nov. 23 and Nov. 25;
- encounter/order identifiers for the medication records, but no field that references `labevent_id=415122` or otherwise declares that a specific medication decision was derived from that result.

HSR-001 does **not** infer that the medication administrations were caused by the potassium result. Shared patient, encounter, clinical plausibility, and temporal proximity are deliberately treated as insufficient evidence of dependency.

The perturbation is synthetic: "suppose this potassium result were later corrected." The record is real; the correction is not claimed to have occurred.

## Positive control: FHIR R4

FHIR R4 `MedicationRequest.reasonReference` can explicitly reference an `Observation` supporting why a prescription was written. HSR-001 includes a synthetic FHIR-shaped control with one medication request explicitly linked to the changed observation and another independent medication request.

The same strict auditor must:

- reopen the explicitly dependent request;
- retain the independent request;
- refuse selective reopening on the MIMIC arm because the required derivation edge is absent.

## Winning condition

The experiment passes if it distinguishes **algorithm capability** from **dependency evidence availability**:

1. positive control: selective reopening works when the dependency is explicit;
2. real-data arm: missing derivation evidence yields `DEPENDENCY_COVERAGE_INSUFFICIENT`, never silent `RETAIN`;
3. same-encounter and temporal heuristics are rejected as authority-bearing dependency evidence.

This is a data-affordance audit, not a clinical decision system. It does not recommend, stop, start, or alter treatment.

`policy_authority: NONE`

`runtime_permission: NONE`
