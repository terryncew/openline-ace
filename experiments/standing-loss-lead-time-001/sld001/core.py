from __future__ import annotations

from hashlib import sha256
import json
from statistics import median
from typing import Any, Iterable


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def hash_object(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def standing_loss_time(case: dict[str, Any]) -> int | None:
    """Return completed reverification time only when standing resolves LOST."""
    if not case.get("dependency_declared"):
        return None
    if case.get("reopen") is None:
        return None
    if case.get("reverify_outcome") != "LOST":
        return None
    return int(case["reopen"]) + int(case["reverify_latency"])


def _naive_time(case: dict[str, Any]) -> int | None:
    change = case.get("change")
    return None if change is None else int(change)


def _ttl_time(case: dict[str, Any], ttl_ticks: int) -> int:
    return int(case["receipt_issued"]) + int(ttl_ticks)


def _lead(signal_time: int | None, headline_time: int) -> int | None:
    return None if signal_time is None else int(headline_time) - int(signal_time)


def _rate(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def _receipt(case: dict[str, Any], previous_hash: str) -> dict[str, Any]:
    t_loss = standing_loss_time(case)
    status = "LOST" if t_loss is not None else (
        "VALID" if case.get("reverify_outcome") == "VALID" else "UNCHANGED"
    )
    body = {
        "schema": "openline.ace.sld001.standing-receipt.v1",
        "case_id": case["case_id"],
        "category": case["category"],
        "dependency_declared": bool(case["dependency_declared"]),
        "change": case.get("change"),
        "reopen": case.get("reopen"),
        "reverify_outcome": case.get("reverify_outcome"),
        "t_resolved": t_loss if t_loss is not None else (
            (int(case["reopen"]) + int(case["reverify_latency"]))
            if case.get("reopen") is not None and case.get("reverify_outcome") == "VALID"
            else None
        ),
        "standing": status,
        "previous_receipt_sha256": previous_hash,
        "policy_authority": "NONE",
        "runtime_permission": "NONE",
    }
    body["receipt_sha256"] = hash_object(body)
    return body


def evaluate(cases: Iterable[dict[str, Any]], prereg: dict[str, Any]) -> dict[str, Any]:
    rows = [dict(c) for c in cases]
    consequential = [c for c in rows if c["category"] in prereg["consequential_categories"]]
    negatives = [c for c in rows if c["category"] in prereg["false_invalidation_negative_controls"]]
    hidden = [c for c in rows if c["category"] == prereg["hidden_dependency_category"]]
    raw = [c for c in rows if c["category"] == prereg["raw_failure_category"]]

    enough = (
        len(rows) >= int(prereg["minimum_cases_total"])
        and len(consequential) >= int(prereg["minimum_consequential_cases"])
        and len(negatives) >= int(prereg["minimum_negative_controls"])
    )

    ttl_ticks = int(prereg["ttl_ticks"])
    olp_leads = [_lead(standing_loss_time(c), int(c["headline"])) for c in consequential]
    naive_leads = [_lead(_naive_time(c), int(c["headline"])) for c in consequential]
    ttl_leads = [_lead(_ttl_time(c, ttl_ticks), int(c["headline"])) for c in consequential]

    if not enough or any(v is None for v in olp_leads):
        verdict = "DATA_INSUFFICIENT"
    else:
        olp_vals = [int(v) for v in olp_leads if v is not None]
        naive_vals = [int(v) for v in naive_leads if v is not None]
        ttl_vals = [int(v) for v in ttl_leads if v is not None]

        olp_false = sum(standing_loss_time(c) is not None for c in negatives)
        naive_false = sum(_naive_time(c) is not None for c in negatives)
        ttl_false = sum(_ttl_time(c, ttl_ticks) <= int(c["headline"]) for c in negatives)

        olp_fir = _rate(olp_false, len(negatives))
        naive_fir = _rate(naive_false, len(negatives))
        ttl_fir = _rate(ttl_false, len(negatives))

        med_olp = float(median(olp_vals))
        med_ttl = float(median(ttl_vals))
        early_fraction = _rate(sum(v > 0 for v in olp_vals), len(olp_vals))
        ratio_ok = olp_fir <= float(prereg["naive_false_invalidation_ratio_max"]) * naive_fir
        ttl_dominates = med_ttl >= med_olp and ttl_fir <= olp_fir

        win = (
            med_olp >= float(prereg["minimum_median_lead_ticks"])
            and early_fraction >= float(prereg["minimum_early_fraction"])
            and ratio_ok
            and not ttl_dominates
        )
        verdict = "STANDING_LOSS_LEAD_TIME_ADVANTAGE" if win else "NO_STANDING_LOSS_ADVANTAGE"

    receipts = []
    prev = "0" * 64
    for case in sorted(rows, key=lambda x: x["case_id"]):
        rec = _receipt(case, prev)
        receipts.append(rec)
        prev = rec["receipt_sha256"]

    def summary(leads: list[int | None]) -> dict[str, Any]:
        vals = [int(v) for v in leads if v is not None]
        return {
            "cases": len(leads),
            "resolved": len(vals),
            "median_lead_ticks": None if not vals else float(median(vals)),
            "positive_lead_fraction": _rate(sum(v > 0 for v in vals), len(vals)),
            "leads": vals,
        }

    olp_false = sum(standing_loss_time(c) is not None for c in negatives)
    naive_false = sum(_naive_time(c) is not None for c in negatives)
    ttl_false = sum(_ttl_time(c, ttl_ticks) <= int(c["headline"]) for c in negatives)

    hidden_misses = sum(standing_loss_time(c) is None and c["headline_outcome"] == "FAIL" for c in hidden)
    raw_no_signal = sum(standing_loss_time(c) is None and c["headline_outcome"] == "FAIL" for c in raw)
    conservative = [c for c in rows if c["category"] == "benign_revocation" and standing_loss_time(c) is not None and c["headline_outcome"] == "PASS"]

    return {
        "schema": "openline.ace.sld001.result.v1",
        "experiment_id": "SLD-001",
        "verdict": verdict,
        "data_boundary": prereg["data_boundary"],
        "case_count": len(rows),
        "consequential_case_count": len(consequential),
        "negative_control_count": len(negatives),
        "lead_time": {
            "headline_only": {
                "cases": len(consequential),
                "resolved": len(consequential),
                "median_lead_ticks": 0.0 if consequential else None,
                "positive_lead_fraction": 0.0,
                "leads": [0 for _ in consequential],
            },
            "olp": summary(olp_leads),
            "naive_diff": summary(naive_leads),
            "ttl": summary(ttl_leads),
        },
        "false_invalidation": {
            "olp": {"events": olp_false, "rate": _rate(olp_false, len(negatives))},
            "naive_diff": {"events": naive_false, "rate": _rate(naive_false, len(negatives))},
            "ttl": {"events": ttl_false, "rate": _rate(ttl_false, len(negatives))},
            "definition": "LOST/alert on frozen negative controls whose dependency-bound standing remains valid after evaluation"
        },
        "coverage_limits": {
            "hidden_dependency_cases": len(hidden),
            "hidden_dependency_misses": hidden_misses,
            "raw_failure_cases": len(raw),
            "raw_failures_without_prior_standing_signal": raw_no_signal,
        },
        "conservative_invalidation_overhead": {
            "events": len(conservative),
            "case_ids": [c["case_id"] for c in conservative],
            "note": "Evidence standing was legitimately lost even though downstream output would have succeeded; these are not counted as false judgments."
        },
        "receipt_chain": {
            "count": len(receipts),
            "head_sha256": prev,
            "receipts": receipts,
        },
        "claims": {
            "prediction": False,
            "universal_external_advantage": False,
            "runtime_safety": False,
            "conformance_only": True,
        },
        "policy_authority": "NONE",
        "runtime_permission": "NONE",
    }
