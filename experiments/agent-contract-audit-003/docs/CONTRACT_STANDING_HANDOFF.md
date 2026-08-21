# Contract Standing Handoff

A-003 occupies the seam between ACE causal standing and receiver-owned downstream use.

**ACE may export standing. ACE may not export permission.**

Eligibility requires a source packet declaring `BLIND_EXTERNAL_RUN_COMPLETED`, independent verification
`PASS`, at least 64 paired rollouts, and `SUPPORTED` standing. Mechanics-only or external-unrun packets
are ineligible even if an internal fixture was supported.

The derived receipt uses Ed25519 and `olp-canonical-json-int-v1`; statistical floats are converted to
integer micros inside the signed disclosure. The raw source packet is not falsely labeled Wire-Canon
data: its identity uses a separately named `json-sort-keys-compact-utf8-v1` hash.

The Claim Graph projection is `UNADMITTED`. The Receipt Gate projection is evidence-only and carries
neither a requested disposition nor a commit authorization.

This proves transport integrity and anti-escalation mechanics only. It does not prove the source contract
is true or grant any receiver authority.
