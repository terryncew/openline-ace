# OpenLine Robotics Constraint Audit 001

RCA-001 is the first ACE Tier-2 robotics protocol pack.

It tests one narrow relation: a high-level locomotion command should continue only while fresh receiver-side evidence says the commanded motion remains inside a stopping envelope.

```text
planner / high-level command
          ↓
 OpenLine standing gate
    COMMIT / DENY
          ↓
 low-level locomotion controller
          ↓
      MuJoCo physics
```

OpenLine does not balance the humanoid or issue joint torques.

The official Unitree MuJoCo repo is used only as the intended external physics/control substrate. The stopping envelope, protected boundary, freshness rule, matched sham, supervisory gate, and causal scheduler are OpenLine scaffolding.

This pack contains a frozen question, deterministic gate, four-arm synthetic conformance harness, independent verifier, external-runner contract, Unitree source pin check, and CI.

The actual G1/MuJoCo locomotion run is intentionally unrun.

Status: `PROTOCOL_CONFORMANCE_PASS_UNITREE_RUN_UNRUN`

Run locally:

```bash
python -m unittest discover -s tests -v
python -m rca001 conformance --out conformance-out
python scripts/verify_conformance_independent.py conformance-out/results.jsonl
python scripts/release_check.py
```

`SUPPORTED_CONFORMANCE_ONLY` is not a robotics safety result.
