# Relational Contract Discovery 005

RCDL-005 is the **Budgeted Causal Utility Tournament**. It tests the remaining
opening after RCDL-004: whether a symbolic relational-contract policy has a
causal intervention, recovery, or explanation advantage over a learned policy
when both receive the same historical interventions, action vocabulary, and
four-query online budget.

The frozen result is **`CAUSAL_UTILITY_PARITY`**. Both policies recovered every
behavioral contract, used three queries per implementation run, correctly
reported the deliberately non-identifiable class, transported across both
execution adapters, and tied on recovery. This rejects *unique* RCDL causal
utility inside this deterministic, action-complete tournament. It does not show
that relational contracts are useless, and it does not test stochastic agents.

## Run it

```bash
cd experiments/relational-contract-discovery-005
export PYTHONPATH="."
python3 -m unittest discover -s tests -v
python3 -m rcdl005 verify-domain
python3 -m rcdl005 verify-policy-boundary
python3 -m rcdl005 verify-oracle
python3 -m rcdl005 verify-evidence
python3 -m rcdl005 run --output causal-utility-out
python3 -m rcdl005 verify-manifest causal-utility-out/causal-utility-manifest.json
python3 -m rcdl005 verify-projection causal-utility-out/verified-handoff-projection.json
```

Regeneration and adversarial checks:

```bash
python3 scripts/freeze_history.py --check
python3 scripts/randomized_probe.py --samples 512
python3 scripts/release_check.py
```

## What is frozen

- four atomic relations;
- ten single- or double-relation interventions;
- one matched sham for every active intervention;
- nine structural mechanisms forming eight observable classes;
- one class that is indistinguishable inside the declared action regime but
  distinguishable with excluded triple-relation interventions;
- 256 held-out scenario identities across two execution adapters;
- four online active interventions per policy;
- verdict and stop rules in `experiment_config.json`.

## Claim boundary

This is a same-builder deterministic calibration. The learned policy has an
action-complete historical signature library. The symbolic policy has the
domain-supplied contract grammar. The two adapters share the official oracle.
There is no external preregistration, independent replication, neural policy,
stochastic LLM, prompt shock, timing shock, or tool transport. Every projection
has policy authority `NONE`.

See `docs/PROTOCOL.md` for the exact comparison and
`docs/NOTEBOOKLM_SOURCE.md` for a study-ready narrative.

