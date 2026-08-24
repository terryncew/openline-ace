# SLD-004 Claim Boundary

SLD-004 tests **selective standing propagation after an external invalidation signal has already been supplied**.

It does not test whether OpenLine discovers vulnerabilities, predicts failures, discovers causal structure, reconstructs undeclared dependencies, or responds faster than the scanner that emitted the signal.

The graph under test is a **declared evidence-dependency DAG**, not a causal DAG. Every historical edge used at `t2` must be source-bound to information available no later than `t1`.

The primary comparison is intentionally strong. `artifact_component_join` receives the same affected component/version signal and exact component membership for each immutable decision artifact. OpenLine earns no credit for merely knowing that a vulnerable package is transitive or present.

Historical lead is reported only as the **available opportunity window** from external signal `t1` to independent visible truth `t3`. SLD-004 does not measure operational propagation latency and therefore cannot claim a speed advantage over the scanner.

The strongest permitted positive F1 claim is:

> On a preregistered historical cohort with public, source-bound decision evidence, evidence-dependency DAG traversal retained materially more independently unaffected decisions than a recall-equivalent strong flat join while reopening at least 95% of affected decisions before later visible resolution.

No F1 claim is permitted from the three-case feasibility stage.

`policy_authority: NONE`  
`runtime_permission: NONE`
