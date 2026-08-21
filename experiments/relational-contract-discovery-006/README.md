# Relational Contract Discovery 006

RCDL-006 is the **EnvHarness Held-Out Mechanism Test**. It uses the real,
pinned EnvHarness `ActionableEnv` and `Rules` core as an intervention substrate
while denying the wrapper any authority over the scientific verdict.

The frozen pilot result is **`HELD_OUT_MECHANISM_CAUSAL_PARITY`**. Symbolic RCDL
and an equal-budget learned signature baseline both correctly distinguished:

- verifier-relevant native failures that invalidated the artifact;
- rules manufactured by a wrapper while the artifact remained valid; and
- harmless representation changes.

Both policies scored 192/192, predicted every recovery horizon, transported
across two held-out agent implementations, and produced zero sham failures.
This supports the native-versus-imposed distinction inside the pilot. It does
not establish unique symbolic utility.

## Run it

Pin the official upstream source beside the ACE checkout:

```bash
git clone https://github.com/google-research/envharness _upstream/envharness
git -C _upstream/envharness checkout fab7d57441f06b75c73a900e04561d4d7600f361
cd experiments/relational-contract-discovery-006
export PYTHONPATH="../../_upstream/envharness:."
python3 -m unittest discover -s tests -v
python3 -m rcdl006 verify-upstream
python3 -m rcdl006 verify-fixtures
python3 -m rcdl006 verify-policy-boundary
python3 -m rcdl006 verify-evidence
python3 -m rcdl006 run --output heldout-mechanism-out
python3 -m rcdl006 verify-manifest heldout-mechanism-out/heldout-mechanism-manifest.json
python3 -m rcdl006 verify-projection heldout-mechanism-out/verified-handoff-projection.json
```

Adversarial checks:

```bash
python3 scripts/randomized_probe.py --samples 512
python3 scripts/release_check.py --samples 384
```

## Frozen boundary

- EnvHarness repository: `google-research/envharness`
- pinned commit: `fab7d57441f06b75c73a900e04561d4d7600f361`
- imported surface: `ActionableEnv`, `Rules`, and their typed contracts
- six development mechanisms and six wholly held-out compositions
- sixteen held-out tasks
- two held-out agent implementations
- active, matched-sham, and restoration arms per case
- three queries per policy per case
- original code-repair verifier as the sole behavioral oracle
- receipt and policy authority: `NONE`

This is still a same-builder deterministic pilot. Proposal fixtures are
EnvRigger-shaped but static and audited; no LLM-generated Python is executed.
See `docs/PROTOCOL.md` for the preregistered logic and
`docs/NOTEBOOKLM_SOURCE.md` for a study-ready explanation.
