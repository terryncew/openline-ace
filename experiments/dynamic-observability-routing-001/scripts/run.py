from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dor001.evaluator import run_all

results = ROOT / "results"
results.mkdir(exist_ok=True)
report = run_all()
(results / "replay_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

with (results / "measurement_receipts.jsonl").open("w", encoding="utf-8") as fh:
    for row in report["rows"]:
        for receipt in row["measurement_receipts"]:
            fh.write(json.dumps({
                "scenario_id": row["scenario_id"],
                "policy": row["policy"],
                **receipt,
            }, sort_keys=True) + "\n")

print(json.dumps({
    "experiment_id": report["experiment_id"],
    "verdict": report["verdict"],
    "primary_metrics": report["primary_metrics"],
}, indent=2, sort_keys=True))
