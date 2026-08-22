# NotebookLM Source — RCA-001

RCA-001 is the first ACE Tier-2 robotics test pack. It asks whether the same perturbation + matched sham + independent oracle + restoration discipline used in software can identify a load-bearing supervisory relation on a physical simulator.

The candidate relation is: high-level locomotion may continue only while fresh receiver-side evidence shows the commanded motion can still stop before a protected boundary.

OpenLine stays above the fast loop. The locomotion controller retains balance, gait, contact, and joint actuation. OpenLine decides only whether a high-level command still has standing.

Baseline preserves the relation. Sham adds matched nuisance without invalidating standing. Active removes the relation. Restoration reinstates it. The oracle measures protected-boundary violation, collision, fall, stopping distance, and task completion.

Unitree supplies only the intended MuJoCo/SDK2 low-level substrate. OpenLine supplies the obstacle/boundary, stopping math, freshness rule, gate, arm scheduler, and causal grader.

Current standing is `PROTOCOL_CONFORMANCE_PASS_UNITREE_RUN_UNRUN`. The synthetic harness is protocol evidence, not a robot-safety result.

A successful external run would not certify hardware safety. It would support the narrower claim that ACE's causal audit logic survives a physical simulation substrate without changing its epistemic rules. Failure, sham contamination, controller-specificity, or restoration failure should narrow or kill that portability claim.
