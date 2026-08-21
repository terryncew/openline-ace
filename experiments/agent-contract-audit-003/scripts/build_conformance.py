from pathlib import Path
import json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from aca003.bundle import build_bundle
out=ROOT/"evidence"/"conformance-bundle"
if out.exists(): shutil.rmtree(out)
p=json.loads((ROOT/"fixtures"/"eligible-supported.json").read_text())
build_bundle(p,out,bytes.fromhex("11"*32))
print("conformance_bundle_built")
