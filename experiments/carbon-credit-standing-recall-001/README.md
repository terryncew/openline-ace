# CCR-001 — Carbon Credit Standing Recall

CCR-001 is the first external-policy replay of OpenLine Selective Reverification outside software history.

The question is narrow:

> When the quantified basis of an already-issued carbon credit is later revised, which downstream standing should reopen, and which recorded facts should remain standing?

The case is Verra VCS project **2372**, *Installation of high efficiency wood burning cookstoves in Malawi — Project 2*.

Boeing's 2024 CDP response reports that specific VCS 2372 serial ranges were retired in Q1 2024 on Boeing's behalf for its Scope 1 and Scope 2 net-zero target, with excess offsets applied to 2023 business-travel emissions. In October 2024, Verra completed a quality-control review and revised project 2372's credited quantity from 4,444,642 issued VCUs to 2,409,500, with 2,035,142 VCUs compensated. Verra's current QCR guidance separately says transferred or retired units retain registry validity, while confirmed excess issuance is compensated and environmental integrity is considered restored if all excess units are replaced.

That creates a real standing asymmetry:

- the **quantification basis changed**;
- the **retirement event did not disappear**;
- the **serial identity did not disappear**;
- the **environmental-integrity basis requires review**;
- a downstream corporate-use claim should be reopened for the receiver's reporting policy, rather than silently inherited or automatically declared false.

## Compared policies

CCR-001 compares three deterministic policies over one frozen dependency declaration:

1. `global_invalidation` — reopen every scored claim after the upstream correction;
2. `flat_registry` — reopen only the claim directly attached to the changed quantification artifact;
3. `selective_reverification` — reopen only scored descendants of the changed basis.

The strict oracle is anchored to external public policy facts. It scores only claims for which the replay package has an explicit standing rule. It does **not** decide whether Boeing's corporate climate disclosure was true or false.

## External-data integrity check

The package freezes Verra's 22 completed C-Quest review rows and verifies:

- the compensated total is exactly **5,004,915 VCUs**;
- for every row with issued VCUs, `issued - revised == compensated`;
- project 2372 equals the published values used by the standing replay.

This catches transcription drift before the replay is scored.

## Winning condition

Selective Reverification passes CCR-001 only if it:

- misses zero oracle-required reopenings;
- creates zero oracle-excess reopenings;
- reviews fewer scored claims than global invalidation;
- misses fewer descendant reopenings than the flat policy;
- preserves the claims the external registry rule explicitly leaves standing.

## What this can establish

A pass means the same selective-reopening mechanism used in the software replay can reproduce one real carbon-market standing asymmetry under a frozen receiver dependency declaration and externally anchored rules.

It does **not** establish automatic dependency discovery, carbon-credit validity in general, the truth of any corporate climate claim, regulatory compliance, or a universal coordination primitive.

`policy_authority: NONE`

`runtime_permission: NONE`
