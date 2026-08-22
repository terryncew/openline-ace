# OpenLine Developmental Memory Audit 001

DMA-001 is the first ACE Tier-4 biological causal-constraint protocol.

It is motivated by Faravelli et al. (Nature, 2026), who showed that human cortical organoids mature over years and that old neural progenitors retain developmental-age information: after reaggregation with young progenitors, old progenitors can respond to young instructive signals while still skipping earlier developmental fates and producing later progeny rapidly.

DMA-001 does **not** claim to identify the molecular mechanism of that temporal memory.

Instead it freezes the audit required for a candidate molecular feature to earn load-bearing standing.

```text
source observation
    -> pre-registered candidate feature
    -> baseline / matched sham / active perturbation / restoration
    -> blinded external fate oracle
    -> paired effect estimate
    -> standing
```

The four required affordances are:

1. manipulable candidate relation;
2. matched sham;
3. independent outcome oracle;
4. verifiable restoration path.

The checked repository fixture is synthetic conformance only. It demonstrates that the grader can:
- support a planted load-bearing candidate;
- reject a correlated ritual;
- abstain when the sham itself damages the system;
- refuse incomplete restoration evidence.

No wet-lab result is included.

## Scientific status

`PROTOCOL_CONFORMANCE_PASS_WETLAB_UNRUN`

`policy_authority: NONE`

`ace_level: 1`

## Intended live question

> Among pre-registered molecular features associated with developmental age in old cortical-organoid progenitors, does perturbing a candidate feature specifically erase or weaken the old-progenitor late-fate bias relative to a matched sham, and does restoring that feature recover the bias?

A candidate only earns `SUPPORTED_LOAD_BEARING` when all frozen conditions pass.

## Run

```bash
cd experiments/developmental-memory-audit-001
python -m unittest discover -s tests -v
python -m dma001 grade --results fixtures/conformance-results.jsonl
python scripts/verify_conformance_independent.py fixtures/conformance-results.jsonl
python scripts/release_check.py
```

## Boundary

DMA-001 is not a consciousness experiment, does not test subjective time perception, and does not equate organoid developmental memory with AI memory.

It is a causal audit protocol for a biological state variable whose existence was motivated by the source paper.

`SUPPORTED` remains evidence. It is not execution authority.
