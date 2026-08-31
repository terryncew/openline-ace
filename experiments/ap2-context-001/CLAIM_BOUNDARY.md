# AP2-CONTEXT-001 claim boundary

This is a pressure test, not an AP2 replacement and not a claim that OpenLine supplies AP2's cryptographic guarantees.

AP2 v0.2 already owns mandate signing, binding, native verification, expiry semantics, key binding, and the protocol's receipt chain. AP2-CONTEXT-001 gives those guarantees full credit.

The experiment asks one narrower question: after malicious pre-authorization context has already shaped a cryptographically valid Open Payment Mandate, does the unchanged OpenLine gate prevent the consequential action from crossing when the receiver's evidence is derived only from that final signed mandate?

No context-provenance repair, new standing rule, semantic-intent binder, or AP2-specific policy is added before the primary run.

A COMMIT is a useful negative result. It means final-artifact validity plus the current OpenLine evidence interface is insufficient to recover user intent once poisoned context has been baked into a valid mandate.

A DENY is a useful positive result only if the denial comes from the unchanged gate and pre-existing receiver evidence, not from new AP2-specific repair logic.

The companion repository remains cited for provenance, but its availability is not part of the verdict. The canonical CI run does not fetch it because the anonymous 4open download endpoint can return HTTP 403 to GitHub-hosted runners. The executable transaction values are frozen from the public paper's AM1 demonstration: user ceiling $50; malicious context broadens authorization to $80 and omits an allowed-payee restriction.
