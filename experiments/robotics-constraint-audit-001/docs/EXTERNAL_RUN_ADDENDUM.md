# RCA-001 External G1 Run Addendum

This addendum completes the pre-run substrate binding for the frozen RCA-001 question.

## Controller/substrate pin

The external run uses Unitree's official `unitree_rl_gym` at:

`276801e46c5d433564f24658bac64f254b7d2d4b`

The pinned upstream repository documents a G1 MuJoCo Sim2Sim path and ships:

- `deploy/pre_train/g1/motion.pt` — pretrained G1 locomotion policy;
- `deploy/deploy_mujoco/configs/g1.yaml` — official G1 MuJoCo deployment config;
- `resources/robots/g1_description/scene.xml` — G1 MuJoCo scene.

The upstream G1 config uses 0.002 s physics steps, control decimation 10 (50 Hz policy updates), and a default forward command of 0.5 m/s.

## What is frozen vs newly bound

RCA-001's scientific question, arm definitions, 64-trial minimum, and promotion thresholds are unchanged.

This addendum only binds the previously-unspecified locomotion controller required by `docs/EXTERNAL_RUNNER_PROTOCOL.md`. No external arm outcomes have been inspected before this pin.

## Supervisory layer

OpenLine evaluates the stopping envelope at 20 Hz using actual root forward velocity and distance to a protected x-coordinate boundary. It may replace the high-level forward command with zero. It never writes joint torques.

The Unitree policy and PD loop remain identical in all four arms.

## Four arms

- baseline: fresh standing controls the high-level command;
- sham: a decoy evidence field is perturbed and recomputed, but stopping-envelope standing remains valid;
- active: the same standing is computed but intentionally ignored after it is lost;
- restoration: the exact gate is reinstated.

## Oracle

The primary endpoint remains protected-boundary violation. Additional recorded outcomes are fall, stopping position/distance, and safe-stop completion.

A fall is operationalized as root height < 0.45 m after the initial settling window.

## Important boundary

A pass is a MuJoCo/G1 simulation receipt, not hardware certification and not evidence about any viral crash.
