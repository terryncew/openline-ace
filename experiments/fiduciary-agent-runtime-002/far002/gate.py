from __future__ import annotations
from .classifier import classify
from .model import Decision, Proposal, Receipt
from .receipts import Registry

ROLES = {
    "TASK_EVALUATION": "TASK_EVALUATOR",
    "META_EVALUATION": "META_EVALUATOR",
    "CONSEQUENCE": "CONSEQUENCE_EVALUATOR",
    "MANDATE": "PRINCIPAL_AUTHORITY",
}

class Gate:
    def __init__(self, registry: Registry):
        self.registry = registry
    def decide(self, proposal: Proposal, receipts: tuple[Receipt, ...]) -> Decision:
        tier, why = classify(proposal)
        if tier == "TIER3_CONSTITUTIONAL":
            return Decision("DENY", ("CONSTITUTIONAL_SURFACE_OUTSIDE_AGENT_AUTHORITY", why), proposal.proposal_id)
        required = {"TASK_EVALUATION", "CONSEQUENCE", "MANDATE"}
        if tier == "TIER2_GENERATOR": required.add("META_EVALUATION")
        by_kind = {r.kind: r for r in receipts}
        missing = sorted(required - set(by_kind))
        if missing:
            return Decision("QUARANTINE", tuple(f"MISSING:{x}" for x in missing), proposal.proposal_id)
        reasons = []
        for kind in sorted(required):
            r = by_kind[kind]
            if not self.registry.verify(r): reasons.append(f"INVALID_SIGNATURE:{kind}")
            if r.subject_id != proposal.proposal_id or r.subject_sha256 != proposal.payload_sha256: reasons.append(f"SUBJECT_MISMATCH:{kind}")
            if r.issuer_id == proposal.actor_id: reasons.append(f"SELF_ISSUED:{kind}")
            if r.issuer_role != ROLES[kind]: reasons.append(f"WRONG_ROLE:{kind}")
        mandate = by_kind["MANDATE"].claims
        if proposal.action not in set(mandate.get("allowed_actions", [])): reasons.append("ACTION_OUT_OF_MANDATE")
        prefixes = tuple(mandate.get("allowed_path_prefixes", []))
        for p in proposal.changed_paths:
            if prefixes and not any(p.startswith(x) for x in prefixes): reasons.append(f"PATH_OUT_OF_MANDATE:{p}")
        if by_kind["TASK_EVALUATION"].claims.get("passed") is not True: reasons.append("TASK_EVALUATION_FAILED")
        if by_kind["CONSEQUENCE"].claims.get("acceptable") is not True: reasons.append("CONSEQUENCE_NOT_ACCEPTABLE")
        if tier == "TIER2_GENERATOR" and by_kind["META_EVALUATION"].claims.get("passed") is not True: reasons.append("META_EVALUATION_FAILED")
        if reasons: return Decision("DENY", tuple(sorted(set(reasons))), proposal.proposal_id, tuple(sorted(r.receipt_id for r in receipts)))
        return Decision("COMMIT", (), proposal.proposal_id, tuple(sorted(r.receipt_id for r in receipts)))
