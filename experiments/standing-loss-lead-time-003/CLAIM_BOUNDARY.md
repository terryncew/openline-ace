# SLD-003 Claim Boundary

SLD-003 tests **dependency-bound standing recall**, not vulnerability prediction.

A positive result may support only this bounded claim:

> In the frozen external corpus, exact-state full dependency graphs captured advisory invalidations that direct-dependency monitoring missed because the affected package was transitive, while event-time rebinding rejected stale snapshot matches; some standing-loss events preceded later dependency remediation.

SLD-003 does **not** establish that:

- advisories predict exploitation or runtime failure;
- every transitive dependency should block execution;
- OSV is a complete vulnerability oracle;
- lockfiles are complete descriptions of runtime dependency use;
- the result generalizes beyond the frozen repositories/ecosystems;
- OpenLine discovers hidden dependencies.

Hidden or omitted dependencies remain a declared blind spot.

`policy_authority: NONE`  
`runtime_permission: NONE`
