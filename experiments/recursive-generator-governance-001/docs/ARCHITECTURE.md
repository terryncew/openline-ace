# Architecture

```text
Tier 1: candidate mutation a_i
    -> E_task
    -> Receipt Gate
    -> local promotion

Tier 2: generator mutation G_t -> G_t+1
    -> conservative classifier
    -> cumulative drift audit
    -> Generator Gate
         Arm A: E_task reuse
         Arm B: rotating / budgeted E_meta
    -> generator revision or quarantine

Tier 3: E_meta / principal constitutional surface
    -> no swarm write authority
    -> out-of-band principal change only

Research measurement:
    completed Arm A + completed Arm B
    -> terminal-only E_external
    -> divergence / capture comparison
```

`E_external` is intentionally distinct from `E_meta`. The Generator Gate is
therefore not graded on the same holdout it adaptively queried.

The reference implementation is an evolutionary search substrate rather than
a hostile process sandbox. The code demonstrates authority routing and evidence
separation; it does not claim OS-level containment against a generator that can
read arbitrary evaluator memory.
