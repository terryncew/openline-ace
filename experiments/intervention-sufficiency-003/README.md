# IS-003 — Unitree Disjoint-Context Confirmatory Grid

IS-003 is the first prospective Unitree confirmatory run after IS-002.

The earlier 50-context Stage A/IS-002 corpus is a discarded design pilot. Its
outcomes do not enter this experiment. IS-003 reconstructs only the pilot's
pre-outcome perturbation tuples so it can prove the new 100-context grid is
disjoint before any new rollout is evaluated.

The grid is frozen at `d163cecdb806f71ec27eb11a621a203179ef0df46ae743fb90879fe701cf3aae` and contains 100 unique contexts: 40
adversarial, 30 clean controls, and 30 recovery candidates. Those labels are
physical-load strata, not outcome labels. Every context is crossed with six
frozen actions and five frozen lags for 3,000 deterministic counterfactual
cells.

A green workflow means the protocol and receipts are valid. The scientific
verdict is written separately; CI does not turn a failed hypothesis into a
software failure.

Run the local freeze check:

```bash
cd experiments/intervention-sufficiency-003
python scripts/release_check.py
```

The external GitHub workflow is manual because it installs the pinned Unitree
controller and MuJoCo stack and executes the 3,000-cell confirmatory run.
