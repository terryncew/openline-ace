from __future__ import annotations
import uuid
from dataclasses import asdict
from .canonical import sign, verify
from .model import Receipt
class Registry:
    def __init__(self,secrets:dict[str,tuple[str,str]]): self._secrets=dict(secrets)
    def role(self,issuer_id):
        row=self._secrets.get(issuer_id); return None if row is None else row[0]
    def issue(self,*,issuer_id,kind,subject_id,subject_sha256,claims):
        role,secret=self._secrets[issuer_id]
        payload={'receipt_id':str(uuid.uuid4()),'issuer_id':issuer_id,'issuer_role':role,'kind':kind,'subject_id':subject_id,'subject_sha256':subject_sha256,'claims':claims}
        return Receipt(**payload,signature=sign(secret,payload))
    def verify(self,receipt):
        row=self._secrets.get(receipt.issuer_id)
        if not row: return False
        role,secret=row; payload=asdict(receipt); sig=payload.pop('signature')
        return receipt.issuer_role==role and verify(secret,payload,sig)
