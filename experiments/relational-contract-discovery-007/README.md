# Relational Contract Discovery 007

RCDL-007 is the **Pre-Adjudication Causal Search Test**.

It removes the verdict leakage identified after RCDL-006. Neither evaluation
policy receives `artifact_valid`, hidden fault sets, standing labels, recovery
horizons, relation names, or any other verdict-derived feature. Both begin with
the same passive `RawObservation`, see the same ten opaque probe IDs, receive
the same raw observation after a selected probe, and have the same four-query
budget.

The learned baseline is intentionally strong. Its development history is
action-complete: it receives the outcome of every probe for every development
family plus the development standing labels. At evaluation time it receives no
hidden labels or topology IDs. Both policies use the same deterministic minimax
partition rule to choose the next probe.

The frozen result is **`PRE_ADJUDICATION_CAUSAL_PARITY`**.

- symbolic RCDL: 320/320 correct, 544 probes total, mean 1.7, max 2;
- learned active baseline: 320/320 correct, 544 probes total, mean 1.7, max 2;
- 640 canonical evaluation rows;
- ten evaluation families, including composition-held-out native, imposed,
  mixed, and nuisance cases;
- two independently implemented adapters;
- zero transport failures;
- 4,096 randomized nuisance comparisons, zero policy mismatches;
- policy authority: `NONE`.

Claim effect: **`UNIQUE_PRE_ADJUDICATION_UTILITY_NOT_FOUND`**.

This is the intended stop condition for the synthetic unique-advantage claim.
RCDL remains useful as an auditable symbolic representation and experiment
protocol, but this pilot does not support a claim that its explicit relational
representation is uniquely better at choosing causal probes.

## Run it

```bash
cd experiments/relational-contract-discovery-007
export PYTHONPATH="."
python3 -m unittest discover -s tests -v
python3 -m rcdl007 verify-evidence
python3 -m rcdl007 run --output pre-adjudication-out
python3 scripts/randomized_probe.py --samples 4096
python3 scripts/release_check.py
```

See `docs/PROTOCOL.md` for the frozen boundary and `docs/NOTEBOOKLM_SOURCE.md`
for the study source.
