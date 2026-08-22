# HDR-001 Result — Cigna / DMHC Enforcement Matter 23-262

## Result

`EXTERNAL_REGULATORY_RECALL_PASS`

On the frozen category fixtures:

| Policy | Required reopenings caught | Missed | Excess reopenings | Review count |
|---|---:|---:|---:|---:|
| Flat process update | 0/2 | 2 | 0 | 0 |
| Global reopen | 2/2 | 0 | 6 | 8 |
| Selective Denial Recall | 2/2 | 0 | 0 | 2 |

The result is intentionally categorical, not epidemiological. The public enforcement record does not disclose the full affected-claim list, so HDR-001 does not estimate how many real claims were reopened or how much money changed hands.

## What the regulator supplied

The external order supplies the key causal structure:

1. Cigna had a filed utilization-management process, UM-11.
2. DMHC found that the targeted retrospective review process did not comply with that filed process.
3. A defined class of denials therefore had to be re-reviewed.
4. The corrective action also named categories that could be excluded from that re-review.

This is stronger than a synthetic "suppose a policy changed" perturbation. The upstream standing loss and the downstream re-review consequence both come from an external regulator.

## What OpenLine adds

OpenLine contributes only the propagation discipline:

- do not treat the process finding as a reason to invalidate every denial everywhere;
- do not leave the process finding isolated at the policy node;
- reopen the descendants that inherited finality from the affected review path;
- preserve explicit exclusions as exclusions, not as medical-validity findings;
- return `UNDETERMINED` when the record does not establish whether a claim belongs to the targeted service class.

## Boundary

`CAP_EXCLUDED` means "this corrective action permits exclusion from this re-review population."

It does **not** mean:

- the service was medically unnecessary;
- the denial was correct;
- the claim should remain unpaid;
- the patient or provider lacks another appeal or legal right.

No patient-specific decision is made by this experiment.
