# NotebookLM Source — DMA-001

## What this experiment is

Developmental Memory Audit 001 is the first attempt to transport ACE's causal-constraint audit into a biological system.

The source paper is Faravelli et al., *Human brain organoids record the passage of time over multiple years*, Nature, published August 19, 2026, DOI 10.1038/s41586-026-10877-x.

The paper showed three things relevant to ACE:

1. cortical organoids can mature over years;
2. transcriptional and methylation state tracks time spent in culture;
3. old progenitors retain developmental-age information after reaggregation and can rapidly produce later neuronal fates even in a young-cell environment.

The paper did **not** identify a single molecular mechanism that stores developmental time.

DMA-001 does not invent one.

## Why ACE fits

ACE requires four affordances:

- a manipulable candidate relation;
- a matched sham;
- an independent outcome oracle;
- a restoration path.

Organoid developmental-memory experiments can, in principle, provide all four.

That makes this a stronger cross-domain test than cosmology, where intervention and restoration are impossible.

## What the live experiment would test

A laboratory would select one molecular feature associated with developmental age and freeze the candidate before perturbation.

The experiment would then compare:

- baseline old-progenitor behavior;
- a matched sham intervention;
- active disruption of the candidate;
- restoration or rescue.

A blinded fate oracle would decide whether the old-progenitor late-fate bias persisted.

The candidate only earns load-bearing standing if active disruption specifically damages the phenotype relative to sham and restoration recovers it.

## What the repository currently proves

Only protocol mechanics.

The synthetic fixture contains:

- one planted load-bearing candidate;
- one correlated ritual;
- one sham-sensitive confound;
- one candidate with missing restoration evidence.

The deterministic grader must support, reject, abstain, and remain incomplete in the correct cases.

## What would be consequential if the live test succeeded

The important result would not be 'ACE explains biology.'

It would be narrower and stronger:

> The same audit logic that distinguishes load-bearing relations from rituals in software can operate on a biological developmental system without changing its epistemic rules.

That would be genuine evidence of substrate portability.

## What would falsify the transfer

The transfer weakens if:

- candidate perturbations cannot be made specifically enough to distinguish mechanism from general toxicity;
- matched shams cannot equalize manipulation burden;
- restoration is not possible or is itself strongly confounded;
- the fate oracle is unstable or dependent on the candidate-selection process;
- supported candidates fail to replicate across batches or cell lines.

## Current standing

`PROTOCOL_CONFORMANCE_PASS_WETLAB_UNRUN`

No biological mechanism has been promoted.

No execution authority is granted.

## Big-picture role

DMA-001 is a Tier-4 bridge.

Agent workflows are ACE's native habitat. Distributed systems give a deterministic second substrate. Robotics would provide a physical control substrate. Developmental organoids offer a biological substrate with unusually clean history-dependent fate behavior.

If the same perturbation + sham + oracle + restoration logic survives across these substrates, ACE earns a broad methodological claim without needing a metaphysical theory of boundaries.
