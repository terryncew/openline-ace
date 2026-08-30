from __future__ import annotations
from dataclasses import dataclass,asdict
import hashlib,json,uuid
@dataclass
class Promotion:
    receipt_id:str; node:str; state_sha256:str; depends_on:tuple[str,...]; evidence_receipts:tuple[str,...]; standing:str='ACTIVE'
class ClaimGraph:
    def __init__(self): self.rows={}; self.node_latest={}
    def add(self,node,state_sha256,depends_on,evidence_receipts):
        r=Promotion(str(uuid.uuid4()),node,state_sha256,tuple(depends_on),tuple(evidence_receipts),'ACTIVE'); self.rows[r.receipt_id]=r; self.node_latest[node]=r.receipt_id; return r
    def latest(self,node):
        rid=self.node_latest.get(node); return self.rows.get(rid) if rid else None
    def revoke(self,receipt_id):
        if receipt_id not in self.rows: raise KeyError(receipt_id)
        self.rows[receipt_id].standing='REVOKED'; changed={receipt_id}
        progress=True
        while progress:
            progress=False
            for rid,row in self.rows.items():
                if row.standing=='ACTIVE' and any(dep in changed or self.rows.get(dep,Promotion('','','',(),(),'ACTIVE')).standing in {'REVOKED','REOPEN'} for dep in row.depends_on):
                    row.standing='REOPEN'; changed.add(rid); progress=True
        return changed
    def node_standing(self): return {n:self.rows[rid].standing for n,rid in self.node_latest.items()}
    def can_rely(self,node):
        row=self.latest(node); return bool(row and row.standing=='ACTIVE')
    def snapshot(self): return [asdict(self.rows[k]) for k in sorted(self.rows)]
class StandingGate:
    def __init__(self,graph): self.graph=graph
    def rely(self,node): return 'COMMIT' if self.graph.can_rely(node) else 'DENY'
