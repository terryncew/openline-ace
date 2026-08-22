# HDR-001 — Health Denial Recall

HDR-001 asks a concrete public-policy question:

> When a regulator finds that a health plan's medical-necessity review process did not comply with the plan's own filed utilization policy, which earlier denials must lose final standing and be re-reviewed?

The external case is California Department of Managed Health Care enforcement matter **23-262** involving Cigna HealthCare of California, Inc.

DMHC found that, for a subset of retrospectively reviewed services, Cigna denied claims as not medically necessary using a process that did not comply with its filed Utilization Management Policy 11 (UM-11). The corrective action plan required Cigna to re-review affected denials arising from dates of service from **2021-06-11 through 2023-06-11**, subject to explicit exclusions.

This is the first OpenLine health-coverage recall case in which the upstream defect, downstream recall duty, date window, and exclusions are all supplied by a public regulator rather than invented by the experiment.

## What is real

The following are externally anchored by the DMHC enforcement record:

- the affected plan and enforcement matter;
- the finding that the targeted retrospective review process did not comply with UM-11;
- the requirement to re-review denials for the defined Services denied for lack of medical necessity in the inclusive date window;
- the explicit exclusion classes:
  - services designated by the relevant Coverage Policy as always experimental, investigational, or unproven;
  - claims later adjusted and paid in full, including claims later overturned through grievance, provider appeal, or independent medical review;
  - non-diagnostic COVID testing described by the order;
- the requirement to revise and re-file UM-11.

## What is synthetic

The individual claim records in `fixtures/claims.json` are synthetic category fixtures. They contain no patient names, identifiers, diagnoses, claim numbers, or protected health information.

They exist only to test whether the recall rule is implemented correctly.

HDR-001 does **not** claim that any fixture corresponds to a real Cigna claim.

## Compared policies

The experiment compares:

1. `flat_process_update` — records the UM-11/process change but does not propagate it to old denials;
2. `global_reopen` — reopens every active denial in the modeled set;
3. `selective_denial_recall` — follows the regulator-defined population, date window, and exclusions.

The external oracle is deliberately narrow: it scores whether a synthetic fixture belongs to the corrective-action re-review set. It does **not** decide whether a medical service was necessary, whether a claim should ultimately be paid, or whether an appeal would succeed.

## Winning condition

Selective Denial Recall passes only if it:

- misses zero fixtures that the CAP says must be re-reviewed;
- reopens zero fixtures the CAP explicitly excludes or places outside scope;
- refuses to infer scope when membership in the targeted service class is unknown;
- beats both flat non-propagation and indiscriminate reopening on the frozen fixture set.

## Why this matters

A denial is not just a historical event. It is a state that can keep producing consequences because later systems treat it as settled.

When the basis that earned that finality is invalidated, the correct question is not "did the denial happen?" It did.

The question is:

> **Does the denial still deserve to be treated as final?**

HDR-001 tests one real regulatory answer: for the affected class, **no — re-review it**.

## Sources

- DMHC Letter of Agreement, Enforcement Matter 23-262:
  https://wpso.dmhc.ca.gov/enfactions/docs/4925/1759934963434.pdf
- DMHC enforcement-action record:
  https://wpso.dmhc.ca.gov/enfactions/actiondisplay.aspx?ActionKey=4925&LinkKey=9053
- DMHC press release, October 8, 2025:
  https://www.dmhc.ca.gov/Resources/Newsroom/PressReleases/October8%2C2025.aspx

`policy_authority: NONE`

`runtime_permission: NONE`

`patient_specific_advice: NONE`
