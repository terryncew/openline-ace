# OpenLine Agent Contract Audit 003 — Contract Standing Handoff

A-003 closes the ACE → receiver seam.

`SUPPORTED` is evidence. It is not `COMMIT`.

The experiment accepts only the shape of a completed, independently verified blind external A-002 run,
then emits a signed standing receipt, disclosure, Claim Graph projection, Receipt Gate evidence projection,
and closed handoff manifest.

The checked fixture is **mechanics only**. It simulates an eligible source packet so the transport can be
attacked; it is not evidence that the live A-002 provider lane has run.

Run:

```bash
cd experiments/agent-contract-audit-003
python -m unittest discover -s tests -v
python scripts/build_conformance.py
python scripts/verify_bundle_independent.py evidence/conformance-bundle
python scripts/release_check.py
```

No output grants policy authority or runtime permission.
