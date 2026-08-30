from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from far006.experiment import adjudicate, recompute_metrics
from far006.external_task import load_task, verify_local_artifacts


parser = argparse.ArgumentParser()
parser.add_argument("--result-dir", required=True)
args = parser.parse_args()
result_dir = pathlib.Path(args.result_dir)
result_path = result_dir / "result.json"
result = json.loads(result_path.read_text())
preregistration = json.loads((ROOT / "PREREGISTRATION.json").read_text())
task = load_task(ROOT)
assert verify_local_artifacts(ROOT, task)["passed"]
assert result["task"]["instance_id"] == task["instance_id"]
assert result["task"]["base_commit"] == task["base_commit"]
assert result["integrity"]["external_dataset_revision"] == task["dataset"]["revision"]
assert result["integrity"]["external_task_manifest_sha256"] == hashlib.sha256(
    (ROOT / "EXTERNAL_TASK.json").read_bytes()
).hexdigest()
assert result["integrity"]["historical_patch_sha256"] == task["historical_fix"]["patch_sha256"]
assert result["integrity"]["oracle_patch_sha256"] == task["oracle"]["test_patch_sha256"]
recomputed_metrics = recompute_metrics(result)
assert result["metrics"] == recomputed_metrics, (result["metrics"], recomputed_metrics)
expected = adjudicate(preregistration, result["metrics"], result["integrity"])
assert result["verdict"] == expected, (result["verdict"], expected)
assert result["scientific_standing"] == "PROSPECTIVE_PRIMARY"
observed_hash = hashlib.sha256(result_path.read_bytes()).hexdigest()
recorded_hash = (result_dir / "result.sha256").read_text().strip()
assert observed_hash == recorded_hash, (observed_hash, recorded_hash)
print("PASS result verdict", expected)
