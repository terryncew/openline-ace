# ACE Cross-Substrate Conformance 001

This is the high-ROI bridge experiment: keep the ACE experimental grammar fixed while the substrate changes.

The frozen question is:

> Can the exact same active / matched-sham / restoration standing rule distinguish a planted load-bearing dependency from a perfect observational ritual across three heterogeneous fixtures?

The three specimens are an agent/software handoff, a replicated-log quorum model, and an unstable feedback-control simulation. Each contains two candidates that are present in every healthy baseline: one really matters; one is ritual.

Expected result:

```text
agent_software_workflow  fresh-test-binding       SUPPORTED
agent_software_workflow  planning-marker          REJECTED_RITUAL
distributed_system       majority-before-commit   SUPPORTED
distributed_system       leader-audit-marker      REJECTED_RITUAL
control_simulation       fresh-sensor-feedback    SUPPORTED
control_simulation       telemetry-marker         REJECTED_RITUAL
```

The grader is substrate-blind. Adapter identity never enters standing. A candidate can earn `SUPPORTED` only when baseline passes, the targeted break fails, the matched sham still passes, and restoration recovers. A sham mismatch forces `UNDECIDABLE`.

## Claim boundary

This proves conformance mechanics only. It does **not** establish external discovery performance, production distributed-system portability, physical robotics portability, a shared cross-domain mechanism, or a universal law. The control specimen is simulation only. No policy authority or runtime permission is created.

## Run

```bash
cd experiments/cross-substrate-conformance-001
python -m unittest discover -s tests -v
python -m ace_xs --out evidence/result.json
python scripts/verify_evidence.py
python scripts/release_check.py
```
