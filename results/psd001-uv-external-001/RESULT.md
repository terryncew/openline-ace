# PSD-001 — Canonical External Result

**Receipt:** `PSD001-UV-EXTERNAL-001`  
**Verdict:** `SELECTIVE_LOCALIZATION_ADVANTAGE`  
**External substrate:** `astral-sh/uv@26a9dd4b2125bc271b47855e1fa0c49af3365db5`  
**OpenLine merge:** `terryncew/openline-ace@a74d04699d0ec397a72f083675d9dc2fcae44520`  
**PR:** #32  
**Workflow run:** `32692778193`  
**Artifact:** `9507841901`  
**Artifact SHA-256:** `9e6dc6f4e1a7a4d89ac7a3e525ea07e17c97beed81563e73e3cbd5af81678c78`

## Frozen result

Across 24 complete blind intervention trials:

- OpenLine evidence binding: recall 1.000, precision 1.000, false-reopen rate 0.000.
- Artifact/component join: recall 1.000, precision 0.415094, false-reopen rate 0.254098.
- Repository-scope join: recall 1.000, precision 0.229167, false-reopen rate 0.606557.
- Equivalent decision-closure index: recall 1.000, precision 1.000, false-reopen rate 0.000.
- Bootstrap 95% CI for artifact-minus-OpenLine false-reopen rate: [0.133739, 0.406475].
- Equivalent-index mismatches: 0.
- Known missing-edge arm: 0 silent false retains; 15 decisions returned `UNDETERMINED`.

## What this earns

On this frozen external substrate, decision-specific evidence binding localized standing loss more selectively than artifact- or repository-level joining while preserving affected-decision recall.

## What this does not earn

The result does not establish early warning, prediction, causal discovery, minimal repair, fast selection, operational speed advantage, generalization beyond this substrate, or unique graph-algorithm superiority. The equivalent flat decision-closure index matched the graph exactly.

The complete external evidence bundle is preserved in this directory so the result no longer depends on the expiring GitHub Actions artifact.

`policy_authority: NONE`  
`runtime_permission: NONE`
