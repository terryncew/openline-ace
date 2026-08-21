from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping
from .canonical import sha256_hex, conventional_json_hash
from .receipt import sign_standing, verify_receipt
from .projections import claim_graph_projection, receipt_gate_projection

def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n",encoding="utf-8")

def build_bundle(packet: Mapping[str, Any], out: Path, private_key_bytes: bytes) -> dict[str, Any]:
    out.mkdir(parents=True,exist_ok=True)
    receipt,disclosure=sign_standing(packet,private_key_bytes)
    verify_receipt(receipt,disclosure)
    cg=claim_graph_projection(receipt,disclosure)
    rg=receipt_gate_projection(receipt,disclosure)
    write_json(out/"contract-standing.receipt.json",receipt)
    write_json(out/"contract-standing.disclosure.json",disclosure)
    write_json(out/"claim-graph.projection.json",cg)
    write_json(out/"receipt-gate.projection.json",rg)
    files={}
    for name in ("contract-standing.receipt.json","contract-standing.disclosure.json","claim-graph.projection.json","receipt-gate.projection.json"):
        data=(out/name).read_bytes()
        files[name]={"sha256":sha256_hex(data),"size":len(data)}
    manifest={
        "profile":"openline.contract-standing-handoff.manifest.v1",
        "files":files,
        "source_packet_hash_profile":"json-sort-keys-compact-utf8-v1",
        "source_packet_sha256":conventional_json_hash(packet),
        "policy_authority":"NONE",
        "runtime_permission":"NONE",
    }
    write_json(out/"handoff-manifest.json",manifest)
    return manifest
