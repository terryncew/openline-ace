from __future__ import annotations

from datetime import date
from typing import Dict, Any, List

WINDOW_START = date.fromisoformat("2021-06-11")
WINDOW_END = date.fromisoformat("2023-06-11")
TARGET_BASIS = "LACK_OF_MEDICAL_NECESSITY"

VALID_MEMBERSHIP = {"YES", "NO", "UNKNOWN"}
VALID_BASIS = {TARGET_BASIS, "OTHER"}

def validate(record: Dict[str, Any]) -> None:
    required = {
        "claim_id", "targeted_service_membership", "date_of_service",
        "denial_basis", "always_eiu", "later_adjusted_paid_or_overturned",
        "non_diagnostic_covid_testing", "expected"
    }
    if set(record) != required:
        raise ValueError("fixture fields must match the frozen schema exactly")
    if record["targeted_service_membership"] not in VALID_MEMBERSHIP:
        raise ValueError("invalid targeted_service_membership")
    if record["denial_basis"] not in VALID_BASIS:
        raise ValueError("invalid denial_basis")
    for k in ("always_eiu", "later_adjusted_paid_or_overturned", "non_diagnostic_covid_testing"):
        if not isinstance(record[k], bool):
            raise ValueError(f"{k} must be boolean")
    date.fromisoformat(record["date_of_service"])

def selective_denial_recall(record: Dict[str, Any]) -> str:
    validate(record)

    if record["targeted_service_membership"] == "UNKNOWN":
        return "UNDETERMINED"

    if record["targeted_service_membership"] == "NO":
        return "OUTSIDE_CAP_SCOPE"

    dos = date.fromisoformat(record["date_of_service"])
    if dos < WINDOW_START or dos > WINDOW_END:
        return "OUTSIDE_CAP_SCOPE"

    if record["denial_basis"] != TARGET_BASIS:
        return "OUTSIDE_CAP_SCOPE"

    if (
        record["always_eiu"]
        or record["later_adjusted_paid_or_overturned"]
        or record["non_diagnostic_covid_testing"]
    ):
        return "CAP_EXCLUDED"

    return "REOPEN_REQUIRED"

def flat_process_update(record: Dict[str, Any]) -> str:
    validate(record)
    if record["targeted_service_membership"] == "UNKNOWN":
        return "UNDETERMINED"
    return "NO_REOPEN"

def global_reopen(record: Dict[str, Any]) -> str:
    validate(record)
    if record["targeted_service_membership"] == "UNKNOWN":
        return "UNDETERMINED"
    return "REOPEN_REQUIRED"

def score(records: List[Dict[str, Any]], method) -> Dict[str, int]:
    gold = {r["claim_id"] for r in records if r["expected"] == "REOPEN_REQUIRED"}
    predicted = {r["claim_id"] for r in records if method(r) == "REOPEN_REQUIRED"}
    return {
        "true_reopenings": len(gold & predicted),
        "missed_reopenings": len(gold - predicted),
        "excess_reopenings": len(predicted - gold),
        "review_count": len(predicted),
    }

def run(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    for r in records:
        validate(r)

    outputs = {}
    for name, fn in [
        ("flat_process_update", flat_process_update),
        ("global_reopen", global_reopen),
        ("selective_denial_recall", selective_denial_recall),
    ]:
        outputs[name] = {
            "dispositions": {r["claim_id"]: fn(r) for r in records},
            "metrics": score(records, fn),
        }

    sel = outputs["selective_denial_recall"]["metrics"]
    flat = outputs["flat_process_update"]["metrics"]
    glob = outputs["global_reopen"]["metrics"]

    passed = (
        sel["missed_reopenings"] == 0
        and sel["excess_reopenings"] == 0
        and flat["missed_reopenings"] > sel["missed_reopenings"]
        and glob["excess_reopenings"] > sel["excess_reopenings"]
        and outputs["selective_denial_recall"]["dispositions"]["unknown-service-membership"] == "UNDETERMINED"
    )

    return {
        "profile": "openline.ace.health-denial-recall.result.v1",
        "case_id": "dmhc-cigna-23-262",
        "status": "EXTERNAL_REGULATORY_RECALL_PASS" if passed else "FAIL",
        "methods": outputs,
        "claim_boundary": [
            "The public DMHC order supplies the process defect, recall window, and exclusion classes.",
            "Fixture records are synthetic category records, not real claims or patients.",
            "CAP_EXCLUDED is not a medical-validity judgment.",
            "The experiment does not decide whether a claim should be paid or whether an appeal will succeed.",
        ],
        "policy_authority": "NONE",
        "runtime_permission": "NONE",
        "patient_specific_advice": "NONE",
    }
