from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = json.loads((ROOT / "PREREGISTRATION.json").read_text(encoding="utf-8"))
errors = []
if p["experiment_id"] != "RECURSIVE-GENERATOR-GOVERNANCE-002":
    errors.append("wrong experiment id")
if p["mechanism_change_from_rgg001"].split(".", 1)[0] != "NONE":
    errors.append("binary mechanism must remain unchanged")
if set(p["search_seeds"]) & set(p["rgg001_search_seeds_for_disjointness_check"]):
    errors.append("search seed overlap with RGG-001")
if len(p["search_seeds"]) != 16 or len(set(p["search_seeds"])) != 16:
    errors.append("expected 16 unique primary seeds")
if p["thresholds"]["min_arm_b_mean_progress_delta"] != 0.005:
    errors.append("absolute progress delta moved")
if p["progress_calibration"]["observed_initial_panel_sd"] > p["thresholds"]["max_preprimary_progress_panel_sd"]:
    errors.append("frozen progress calibration exceeds preregistered noise ceiling")
if "quarantine" not in p["anti_rescue"].lower():
    errors.append("anti-rescue must forbid adding quarantine to RGG-002")
if errors:
    raise SystemExit("preregistration failure " + "; ".join(errors))
print("PASS preregistration fresh_seeds=16 delta=0.005 no_quarantine=True")
