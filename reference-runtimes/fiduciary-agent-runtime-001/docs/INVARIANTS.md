# Runtime invariants

1. A proposal cannot satisfy a required evidence slot with a receipt signed by its own actor identity.
2. Evaluation roles cannot satisfy the `MANDATE` slot.
3. Every receipt is subject-bound and payload-bound.
4. Expired evidence produces `QUARANTINE`; revoked, tampered, self-issued, wrong-role, out-of-scope, or failed evidence produces `DENY`.
5. Generator/search/retrieval/policy surfaces default to Tier 2 and require independent meta evidence.
6. The Gate signs its own decision receipt, which depends on every receipt used to adjudicate the proposal.
7. Standing loss propagates through receipt dependencies and reopens affected historical decisions.
8. A previous COMMIT never substitutes for current standing on a later attempt.
9. The reference runtime grants no policy-selection or execution authority to ACE/evaluator outputs.
10. Production cryptography and distributed freshness are adapter obligations, not claims of this reference implementation.
