# Claim Boundary

HSR-001 earns only the following claims:

- The frozen MIMIC-IV demo excerpt contains real deidentified lab and medication-administration records from the same hospitalization.
- Those frozen record schemas do not provide an explicit reference from the selected medication administrations to the selected potassium lab event.
- Shared subject, hospitalization, and temporal proximity do not by themselves establish derivation.
- A synthetic FHIR R4 positive control demonstrates that strict selective reopening is expressible when an explicit Observation → MedicationRequest dependency is supplied.
- Therefore this tested MIMIC-style record is insufficient, by itself, to support safe selective reopening of downstream medication standing after a hypothetical correction to the selected lab result.

HSR-001 does **not** prove:

- that no EHR can encode clinical derivation;
- that FHIR deployments populate `reasonReference` reliably;
- that the selected medication administrations were or were not caused by the selected potassium result;
- that a clinical action should be changed;
- that healthcare standing recall is validated in production.

The safe result under missing dependency evidence is `DEPENDENCY_COVERAGE_INSUFFICIENT`, not `RETAIN`.
