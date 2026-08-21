from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
MIN=-9007199254740991; MAX=9007199254740991
E={'"':'\\"','\\':'\\\\','\b':'\\b','\f':'\\f','\n':'\\n','\r':'\\r','\t':'\\t'}
def s(v):
    o=[]
    for ch in v:
        if ch in E:o.append(E[ch])
        elif ord(ch)<0x20 or ord(ch)>0x7f:o.append(f"\\u{ord(ch):04x}")
        else:o.append(ch)
    return '"'+"".join(o)+'"'
def c(v):
    if v is None:return"null"
    if v is True:return"true"
    if v is False:return"false"
    if type(v)is int:
        if not MIN<=v<=MAX:raise ValueError
        return str(v)
    if type(v)is float:raise ValueError
    if isinstance(v,str):return s(v)
    if isinstance(v,list):return"["+",".join(c(x) for x in v)+"]"
    if isinstance(v,dict):return"{"+",".join(s(k)+":"+c(v[k]) for k in sorted(v))+"}"
    raise TypeError
def cb(v):return c(v).encode("ascii")
def h(b):return hashlib.sha256(b).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("bundle"); a=ap.parse_args(); root=Path(a.bundle)
    r=json.loads((root/"contract-standing.receipt.json").read_text()); d=json.loads((root/"contract-standing.disclosure.json").read_text()); m=json.loads((root/"handoff-manifest.json").read_text())
    body={k:v for k,v in r.items() if k not in {"payload_hash","signature"}}; bb=cb(body)
    assert r["payload_hash"]==h(bb); assert r["disclosure_sha256"]==h(cb(d))
    sig=r["signature"]; Ed25519PublicKey.from_public_bytes(bytes.fromhex(sig["public_key"])).verify(bytes.fromhex(sig["value"]),bb)
    assert r["policy_authority"]=="NONE" and r["runtime_permission"]=="NONE" and r["receiver_admission_required"] is True
    cg=json.loads((root/"claim-graph.projection.json").read_text()); rg=json.loads((root/"receipt-gate.projection.json").read_text())
    assert cg["policy_authority"]=="NONE" and cg["candidate_relation"]["admission_status"]=="UNADMITTED"
    assert rg["policy_authority"]=="NONE" and rg["evidence_only"] is True and rg["requested_disposition"] is None and rg["commit_authorization"] is None
    for name,meta in m["files"].items():
        data=(root/name).read_bytes(); assert len(data)==meta["size"] and h(data)==meta["sha256"]
    print("independent_contract_standing_bundle_verified")
if __name__=="__main__":main()
