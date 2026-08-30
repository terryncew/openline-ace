from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = json.loads((ROOT / "PREREGISTRATION.json").read_text(encoding="utf-8"))

if p["scientific_standing"] != "PROTOCOL_FROZEN_PRE_PRIMARY_OUTCOME":
    raise SystemExit("preregistration standing changed")
if len(p["search_seeds"]) < 8 or len(set(p["search_seeds"])) != len(p["search_seeds"]):
    raise SystemExit("search seeds must be unique and frozen")
if p["protocol"]["meta_query_budget_per_epoch"] * p["protocol"]["meta_rotation_every_generations"] <= 0:
    raise SystemExit("invalid meta query budget")
if not p["positive_control"]["must_pass_before_primary_interpretation"]:
    raise SystemExit("positive control must gate interpretation")
if p["positive_control"]["primary_claim_evidence"]:
    raise SystemExit("positive control cannot count as primary evidence")
if p["constitutional_evaluator_mutation_authority"] != "PRINCIPAL_OUT_OF_BAND_ONLY":
    raise SystemExit("constitutional floor changed")
print("PASS preregistration")
