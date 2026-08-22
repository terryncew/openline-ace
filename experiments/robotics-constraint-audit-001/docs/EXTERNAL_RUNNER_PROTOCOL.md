# External Runner Protocol

A future runner must use the same pinned locomotion controller across all four arms and bind `unitreerobotics/unitree_mujoco@ae6a8403e272733e9996ef59990880330496177f`.

Input includes trial id, arm, seed, G1 robot id, initial speed, protected boundary, supervisory frequency, freshness limit, reaction time, minimum deceleration, and safety margin.

Output must include protected-boundary violation, collision, fall, stopping distance, task completion, immutable controller id, and Unitree commit.

The runner owns simulator startup, low-level controller, high-level setpoint translation, and physical observables. It does not own candidate selection, causal standing, promotion thresholds, or final ACE grade.

The sham reproduces supervisory nuisance without invalidating the envelope. The active arm breaks only the standing relation. Restoration reinstates the exact gate; it may not use an easier scenario or stronger controller.

A separate verifier recomputes schedule, outcomes, deltas, counts, and standing. The runner may never grade itself.
