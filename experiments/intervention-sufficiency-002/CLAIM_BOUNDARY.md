# Claim boundary

INTERVENTION-SUFFICIENCY-002 can establish only that the pinned Unitree Stage A
corpus contains the declared minimum contrast for a fresh state-conditioned
transition benchmark.

It cannot establish that:

- the earlier Stage B result was prospectively confirmed;
- a transition model is accurate, calibrated, or controller-robust;
- the feasible action set is complete outside the frozen controller and model;
- preserving optionality improves recovery;
- simulation transfers to physical hardware;
- an action is authorized to execute; or
- a domain-independent recoverability scalar exists.

The external replay is explicitly `RETROSPECTIVE_DIAGNOSTIC_ONLY`. The source
dataset and prior Stage B result predate this gate.

Authority remains separated:

- transition model: `NONE`
- feasible-set evaluator: `NONE`
- policy selector: `PROPOSAL_ONLY`
- execution: `RECEIVER_OWNED_GATE_REQUIRED`
