# FL-001 protocol

## Governing question

When a receiver is explicitly told that an input has lost evidentiary standing, does that input actually stop affecting downstream judgment and action?

## Frozen causal contrasts

For receiver `r` and case `i`, compare within-receiver, case-paired treatment deltas. Raw performance across models is not the target.

Primary contrasts:

1. `accusation_refuted - control`: residual accusation debt after correction.
2. `accusation_refuted - matched_nuisance`: accusation-specific effect beyond extra text/negative administrative structure.
3. `accusation_refuted - accusation_refuted_evidence_first`: order sensitivity.
4. `explicit_revocation - control`: revocation leakage when the accusation is explicitly labeled withdrawn.
5. `angry_defense - calm_defense`: incremental defense-tone penalty with factual content held fixed.
6. Basis contamination: whether `[A]`, `[N]`, or `[D]` is cited as evidence despite the prompt contract.
7. Cross-receiver heterogeneity of 1–6.

## Controls

Hold fixed case facts, evidence IDs, system prompt, output schema, tools, browsing state, conversation history, retrieval, and decoding settings where providers expose equivalents. Change presentation arm and receiving model separately. Use isolated runs.

The eight subjects are neutral identifiers (`Subject-01` ... `Subject-08`) to avoid unnecessary demographic cues.

## Receiver contract

The receiver is told that allegations are claims rather than evidence, emotional style is non-evidentiary absent independent support, and explicit standing labels must be honored. In the explicit-revocation arm, `[A]` is marked `STANDING: WITHDRAWN` while evidence and refutation are marked `ACTIVE`.

## Fail-closed data contract

Every receiver/case must contain all seven arms with exactly the same replicate IDs. Duplicate `(receiver, case, arm, replicate)` rows are rejected. Malformed scores/actions/basis lists are rejected.

## Outcomes

- `wrongdoing_probability`: 0–100.
- `standing`: 0–100, where 100 means the supplied record creates no reason to reduce neutral standing.
- `recommended_action`: `no_action`, `monitor`, `formal_review`, `temporary_restriction`, or `sanction`.
- `basis_ids`: record tags actually used as evidence.
- `reason`: retained for audit, not sentiment-scored.

## Interpretation

A positive accusation-debt effect alone does not establish a new mechanism. The strongest result is explicit revocation leakage that survives the matched-nuisance and order controls, changes consequential outputs, and differs reproducibly by receiver.

If receiver identity merely rescales judgments or the effect reduces to known order/tone effects, Frame Ledger does not earn a distinct mechanism claim.
