# RCA-001 Frozen Question

Can a receiver-side stopping-envelope check distinguish a genuinely load-bearing supervisory relation from matched computational nuisance, and can restoration of fresh envelope evidence recover safe continuation without entering the robot's low-level torque-control loop?

## External substrate
- `unitreerobotics/unitree_mujoco@ae6a8403e272733e9996ef59990880330496177f`
- intended robot: Unitree G1
- upstream role: MuJoCo/SDK2 low-level simulation substrate only

Unitree's README says the current simulator mainly supports low-level development for sim-to-real controller verification and exposes `LowCmd`, `LowState`, `SportModeState`, and G1 `IMUState`.

## Candidate C
A high-level locomotion command may continue only while fresh receiver-recomputed stopping-envelope evidence shows the motion can still stop before a predeclared protected boundary plus safety margin.

## Four arms
1. baseline — fresh valid envelope evidence.
2. sham — matched supervisory compute/latency nuisance while evidence stays valid.
3. active — break C by allowing continuation after envelope standing is lost.
4. restoration — reinstate the exact receiver-side standing check.

## Outcomes
Primary: `protected_boundary_violation`.
Secondary: collision, fall, stopping distance, task completion.

## Frozen trial budget
- 64 trials per arm minimum.
- identical seed schedule across arms.
- same low-level locomotion controller across all arms.
- sham latency distribution frozen before the run.
- no post-outcome arm-specific retuning.

## External promotion threshold
`SIMULATED_PHYSICAL_SEPARATION` requires baseline and sham violation rates <= 0.05, active-minus-sham delta >= 0.40, restoration violation rate <= 0.05, recovery >= 0.40, full trial counts, and zero independent-replay mismatches.

## Boundary
No real crash diagnosis. No torque control. No hardware certification. No sim-to-real safety claim. No substrate-portability claim until the external four-arm run succeeds.

Current status: `PROTOCOL_CONFORMANCE_PASS_UNITREE_RUN_UNRUN`

`policy_authority: NONE`
