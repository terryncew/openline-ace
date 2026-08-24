# Ginkgo External Trial-Selector Confirmation 001

**Status before external run:** `EXTERNAL_RUN_READY_UNRUN`  
**Policy authority:** `NONE`  
**Runtime permission:** `NONE`

This is the external confirmation already required by the frozen Jain sequential-assay-selector line. It is not a replacement for Candidate Promotion Gate and does not revive the CPG biological-selection claim.

## Plain-language question

When a candidate has no known hard liability yet because some critical assays are still missing, can the frozen selector choose the **next assay** better than fair alternatives?

Every strategy sees the same candidate pool, the same frozen liability rules, the same complete retrospective ground truth, and the same unit assay cost. No strategy can change the final liability definitions or promote a candidate.

The target strategy uses only measurements already revealed for the held-out antibody. It estimates which remaining assay is most likely to expose a declared liability and measures that assay next. The trace stops at the first liability.

## Independent panel

GDPa1 v1.2 is pinned to an exact Ginkgo repository commit, Git blob, path, and byte size. The frozen 137-name Jain identity projection used only for overlap exclusion is embedded locally and hash-bound to its `openline-receipt-gate` provenance, so this experiment has no cross-repository filesystem dependency. The primary cohort:

1. excludes exact normalized antibody-name overlap with the canonical 137-antibody Jain cohort;
2. requires complete values across the nine prospectively frozen Ginkgo assays;
3. performs no imputation;
4. fails source binding on duplicate normalized candidate identities.

The nine external liability thresholds come from the prospectively frozen 2025 PROPHET-Ab approved-antibody warning criteria, not from outcome-dependent fitting on this selector run.

## Fair comparators

- fixed prevalence order;
- greedy fixed coverage;
- uniform random expected order;
- binary threshold-only dynamic selector;
- entropy/information-gain selector using the same frozen risk estimator but choosing maximum Bernoulli uncertainty rather than maximum predicted liability risk.

The headline comparator is whichever admissible baseline has the lowest mean assay cost to first liability, with a frozen tie-break on false reassurance at three assays and then strategy name.

## Positive result

A positive verdict requires all of the following after the data-sufficiency gate:

- target mean assay cost is strictly lower than the strongest comparator;
- paired 10,000-resample bootstrap 95% CI for target-minus-comparator mean cost is entirely below zero;
- target false reassurance at the frozen three-assay budget is no worse than the strongest comparator.

Otherwise the external generalization claim fails. `DATA_INSUFFICIENT`, source access failure, and source binding failure are separate outcomes and cannot be repaired inside this experiment after first scoring.

## Run

```bash
python -m unittest discover -s tests -v
python scripts/verify_freeze.py
python scripts/verify_release.py
python scripts/run_external.py
python scripts/verify_result.py
```

The external run is intentionally absent from the committed release. CI writes the source projection, cohort, traces, and result as evidence artifacts.
