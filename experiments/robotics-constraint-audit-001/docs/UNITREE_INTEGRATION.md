# Unitree Integration Boundary

Pinned upstream: `unitreerobotics/unitree_mujoco@ae6a8403e272733e9996ef59990880330496177f`.

Unitree supplies the intended MuJoCo/SDK2 low-level simulation substrate. Its README explicitly frames the current simulator as mainly for low-level development and sim-to-real controller verification and lists `LowCmd`, `LowState`, `SportModeState`, and G1 `IMUState`.

OpenLine supplies the protected boundary, stopping-envelope formula, freshness rule, continue/stop abstraction, matched sham, four-arm scheduler, gate, and grading.

The external run remains unrun because the upstream simulator does not itself provide this high-level stopping-envelope experiment or a universal G1 locomotion policy. A controller must be frozen before outcomes are observed.
