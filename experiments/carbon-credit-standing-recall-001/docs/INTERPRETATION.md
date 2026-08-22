# Interpretation Note

CCR-001 intentionally separates **event facts** from **standing judgments**.

The public record supports three different statements that should not be collapsed:

1. **Retirement happened.** Boeing reported specific VCS 2372 serial ranges as retired in Q1 2024.
2. **The project's credited quantity was later revised.** Verra reported 4,444,642 VCUs issued, a revised amount of 2,409,500, and 2,035,142 VCUs compensated for project 2372.
3. **Registry validity and environmental integrity are not the same state.** Verra's QCR guidance says previously transferred/retired units retain registry validity, while excess issuance is handled through replacement/compensation; if all excess is replaced, Verra considers environmental integrity restored.

Therefore CCR-001 never rewrites the historical retirement event merely because the quantification basis changed.

Instead it asks whether claims that **inherited environmental standing** from that basis should be reopened for review.

The replay's corporate-use node is deliberately phrased as `boeing-offset-use-standing`, not `boeing-claim-false`. A receiver may need a separate corporate-reporting standard to decide final disposition. CCR-001 only tests whether the upstream correction should interrupt silent inheritance.

## Logical event ordering

Verra announced the project-level correction and compensation in the same October 17, 2024 communication. CCR-001 decomposes those into two logical events for auditability:

- `quantification_revision`: the prior quantity basis loses standing;
- `compensation_processed`: a restoration path becomes available under Verra's own QCR rule.

This is a logical decomposition, not a claim that the two events occurred on different calendar dates.

## Why project 2372

Project 2372 is useful because the public record contains both sides of the dependency:

- a named downstream corporate retirement/use disclosure with serial ranges; and
- a later named project-level quantity correction.

No cooperation from Boeing, Verra, C-Quest, or another market participant is required to run the replay.
