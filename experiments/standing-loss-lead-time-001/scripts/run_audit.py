from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sld001.core import evaluate

cases = json.loads((ROOT / "frozen_cases.json").read_text())
prereg = json.loads((ROOT / "preregistration.json").read_text())
freeze = json.loads((ROOT / "FREEZE.json").read_text())

result = evaluate(cases, prereg)
result["preregistration_sha256"] = freeze["preregistration_sha256"]
result["frozen_cases_sha256"] = freeze["frozen_cases_sha256"]
(ROOT / "results" / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
with (ROOT / "results" / "standing_receipts.jsonl").open("w") as f:
    for rec in result["receipt_chain"]["receipts"]:
        f.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")
print(json.dumps({k: result[k] for k in ["experiment_id", "verdict", "case_count", "lead_time", "false_invalidation", "coverage_limits", "conservative_invalidation_overhead"]}, indent=2, sort_keys=True))
