# Claim boundary

INTERVENTION-SUFFICIENCY-001 is a data-admission gate.

It can establish that a candidate corpus contains the minimum declared support
for testing whether state improves action-conditioned recovery prediction over
an action-plus-delay baseline.

It cannot establish that:

- a transition model is accurate or calibrated;
- a feasible action set is complete;
- a capacity objective improves safety or recovery;
- simulation transfers to hardware;
- a selected action is authorized to execute; or
- a domain-independent recoverability margin exists.

The synthetic controls verify checker mechanics only. External standing remains
`UNRUN` until a separately produced corpus passes this frozen gate.

Authority:

- transition model: `NONE`
- feasible-set evaluator: `NONE`
- policy selector: `PROPOSAL_ONLY`
- execution: `RECEIVER_OWNED_GATE_REQUIRED`
