from __future__ import annotations
import argparse,json
from pathlib import Path
from .bundle import build_bundle
from .receipt import verify_receipt
TEST_KEY=bytes.fromhex("11"*32)

def main():
    p=argparse.ArgumentParser()
    s=p.add_subparsers(dest="cmd",required=True)
    b=s.add_parser("build"); b.add_argument("--packet",required=True); b.add_argument("--output",required=True)
    v=s.add_parser("verify"); v.add_argument("--bundle",required=True)
    a=p.parse_args()
    if a.cmd=="build":
        packet=json.loads(Path(a.packet).read_text(encoding="utf-8"))
        print(json.dumps(build_bundle(packet,Path(a.output),TEST_KEY),sort_keys=True))
    else:
        root=Path(a.bundle)
        r=json.loads((root/"contract-standing.receipt.json").read_text())
        d=json.loads((root/"contract-standing.disclosure.json").read_text())
        verify_receipt(r,d)
        print("contract_standing_bundle_verified")
if __name__=="__main__": main()
