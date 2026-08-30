from __future__ import annotations

import argparse
import json
import os
import pathlib


parser = argparse.ArgumentParser()
parser.add_argument("--result", required=True)
args = parser.parse_args()
result = json.loads(pathlib.Path(args.result).read_text())
metrics = result["metrics"]
lines = [
    "# FAR-006",
    "",
    f"**Verdict:** `{result['verdict']}`",
    "",
    f"**Standing:** `{result['scientific_standing']}`",
    "",
    f"**External baseline failure observed:** `{metrics['external_baseline_failure_observed']:.3f}`",
    "",
    f"**Historical target / consequence pass:** `{metrics['external_historical_fix_target_pass']:.3f}` / `{metrics['external_historical_fix_consequence_pass']:.3f}`",
    "",
    f"**Target-only regression rejected:** `{metrics['local_only_regression_rejection_rate']:.3f}`",
    "",
    f"**Historical fix promoted:** `{metrics['historical_fix_promotion_rate']:.3f}`",
    "",
    f"**Authority escape admission:** `{metrics['authority_escape_admission_rate']:.3f}`",
    "",
    f"**Recall coverage / precision:** `{metrics['recall_coverage']:.3f}` / `{metrics['recall_precision']:.3f}`",
    "",
    f"**Post-recall main reliance blocked:** `{metrics['post_recall_reliance_block_rate']:.3f}`",
]
pathlib.Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text("\n".join(lines) + "\n")
