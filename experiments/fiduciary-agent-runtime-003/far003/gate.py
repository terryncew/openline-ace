from __future__ import annotations
from .classifier import classify
from .model import Decision, Proposal, Receipt
from .receipts import Registry
ROLES={'TASK_EVALUATION':'TASK_EVALUATOR','META_EVALUATION':'META_EVALUATOR','CONSEQUENCE':'CONSEQUENCE_EVALUATOR','MANDATE':'PRINCIPAL_AUTHORITY'}
class Gate:
    def __init__(self,registry:Registry): self.registry=registry
    def decide(self,proposal:Proposal,receipts:tuple[Receipt,...]):
        tier,why=classify(proposal)
        if tier=='TIER3_CONSTITUTIONAL': return Decision('DENY',('CONSTITUTIONAL_SURFACE_OUTSIDE_AGENT_AUTHORITY',why),proposal.proposal_id)
        required={'TASK_EVALUATION','CONSEQUENCE','MANDATE'}
        if tier=='TIER2_GENERATOR': required.add('META_EVALUATION')
        by={r.kind:r for r in receipts}; missing=sorted(required-set(by))
        if missing: return Decision('QUARANTINE',tuple(f'MISSING:{x}' for x in missing),proposal.proposal_id)
        reasons=[]
        for kind in sorted(required):
            r=by[kind]
            if not self.registry.verify(r): reasons.append(f'INVALID_SIGNATURE:{kind}')
            if r.subject_id!=proposal.proposal_id or r.subject_sha256!=proposal.payload_sha256: reasons.append(f'SUBJECT_MISMATCH:{kind}')
            if r.issuer_id==proposal.actor_id: reasons.append(f'SELF_ISSUED:{kind}')
            if r.issuer_role!=ROLES[kind]: reasons.append(f'WRONG_ROLE:{kind}')
        mandate=by['MANDATE'].claims; allowed=set(mandate.get('allowed_actions',[])); prefixes=tuple(mandate.get('allowed_path_prefixes',[]))
        if proposal.action not in allowed: reasons.append('ACTION_OUT_OF_MANDATE')
        for p in proposal.changed_paths:
            if prefixes and not any(p.startswith(x) for x in prefixes): reasons.append(f'PATH_OUT_OF_MANDATE:{p}')
        if by['TASK_EVALUATION'].claims.get('passed') is not True: reasons.append('TASK_EVALUATION_FAILED')
        if by['CONSEQUENCE'].claims.get('acceptable') is not True: reasons.append('CONSEQUENCE_NOT_ACCEPTABLE')
        if tier=='TIER2_GENERATOR' and by['META_EVALUATION'].claims.get('passed') is not True: reasons.append('META_EVALUATION_FAILED')
        if reasons: return Decision('DENY',tuple(sorted(set(reasons))),proposal.proposal_id,tuple(sorted(r.receipt_id for r in receipts)))
        return Decision('COMMIT',(),proposal.proposal_id,tuple(sorted(r.receipt_id for r in receipts)))
