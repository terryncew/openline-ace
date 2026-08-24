from pathlib import Path
from hashlib import sha256
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dor001.evaluator import run_all

report_path = ROOT / "results" / "replay_report.json"
frozen = json.loads(report_path.read_text())
rerun = json.loads(json.dumps(run_all(), sort_keys=True))
if frozen != rerun:
    raise SystemExit("DOR-001 replay mismatch")

checks = {
    "verdict": frozen["verdict"] == "NO_ROUTING_ADVANTAGE",
    "equal_budget": frozen["primary_metrics"]["equal_budget_per_tick"] is True,
    "sentinel": frozen["primary_metrics"]["mandatory_sentinel_coverage"] is True,
    "runtime_permission": frozen["runtime_permission"] == "NONE",
    "policy_authority": frozen["policy_authority"] == "NONE",
    "false_resolution": frozen["primary_metrics"]["false_resolution_events"]["dor"] == 0,
}
if not all(checks.values()):
    raise SystemExit(json.dumps(checks, sort_keys=True))

digest = sha256(report_path.read_bytes()).hexdigest()
print(json.dumps({"valid": True, "checks": checks, "replay_report_sha256": digest}, indent=2, sort_keys=True))
