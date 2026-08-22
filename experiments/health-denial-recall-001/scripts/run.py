from __future__ import annotations
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from hdr001.recall import run

records = json.loads((HERE / "fixtures" / "claims.json").read_text())
result = run(records)
out = HERE / "evidence" / "result.json"
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps(result, indent=2, sort_keys=True))
if result["status"] != "EXTERNAL_REGULATORY_RECALL_PASS":
    raise SystemExit(1)
