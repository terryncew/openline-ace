from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Any, Iterable

DECISIVE = {"APPROVED", "CHANGES_REQUESTED"}


def _ts(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def _hours(seconds: float) -> float:
    return seconds / 3600.0


def build_case(
    candidate: dict[str, Any],
    reviews: list[dict[str, Any]],
    commits: list[dict[str, Any]],
) -> dict[str, Any]:
    """Project one public PR history into the frozen SLD-002 state machine."""
    case = {
        "case_id": f"{candidate['repository']}#{candidate['number']}",
        "repository": candidate["repository"],
        "number": int(candidate["number"]),
        "stratum": candidate["stratum"],
        "headline_at": candidate.get("closed_at"),
        "eligible": False,
        "ineligibility_reason": None,
        "baseline_approval": None,
        "change": None,
        "reverify": None,
        "standing_loss_at": None,
        "standing_after_reverify": "UNRESOLVED",
        "policy_authority": "NONE",
        "runtime_permission": "NONE",
    }
    if candidate.get("history_truncated"):
        case["ineligibility_reason"] = "history_truncated"
        return case
    if not case["headline_at"]:
        case["ineligibility_reason"] = "missing_closed_at"
        return case

    commit_rows = []
    for c in commits:
        commit_sha = c.get("sha")
        date = (
            (((c.get("commit") or {}).get("committer") or {}).get("date"))
            or (((c.get("commit") or {}).get("author") or {}).get("date"))
        )
        if commit_sha and date:
            commit_rows.append((commit_sha, date, _ts(date)))
    commit_rows.sort(key=lambda x: (x[2], x[0]))
    commit_time = {commit_sha: t for commit_sha, _, t in commit_rows}

    decisive = []
    for r in reviews:
        state = r.get("state")
        submitted = r.get("submitted_at")
        commit_id = r.get("commit_id")
        if state in DECISIVE and submitted and commit_id in commit_time:
            decisive.append(
                {
                    "state": state,
                    "submitted_at": submitted,
                    "submitted_ts": _ts(submitted),
                    "commit_id": commit_id,
                    "review_id": r.get("id"),
                }
            )
    decisive.sort(key=lambda x: (x["submitted_ts"], str(x.get("review_id"))))

    headline_ts = _ts(case["headline_at"])
    baseline = None
    first_change = None
    for r in decisive:
        if r["state"] != "APPROVED" or r["submitted_ts"] >= headline_ts:
            continue
        later = [
            (commit_sha, date, t)
            for commit_sha, date, t in commit_rows
            if r["submitted_ts"] < t < headline_ts
        ]
        if later:
            baseline = r
            first_change = later[0]
            break

    if baseline is None or first_change is None:
        case["ineligibility_reason"] = "no_approved_state_with_later_commit"
        return case

    case["eligible"] = True
    case["baseline_approval"] = {
        "commit_id": baseline["commit_id"],
        "submitted_at": baseline["submitted_at"],
        "review_id": baseline["review_id"],
    }
    case["change"] = {
        "commit_id": first_change[0],
        "committed_at": first_change[1],
    }

    reverify = None
    for r in decisive:
        if r["submitted_ts"] <= first_change[2] or r["submitted_ts"] >= headline_ts:
            continue
        if r["commit_id"] == baseline["commit_id"]:
            continue
        commit_ts = commit_time.get(r["commit_id"])
        if commit_ts is None or commit_ts < first_change[2]:
            continue
        reverify = r
        break

    if reverify is None:
        return case

    case["reverify"] = {
        "state": reverify["state"],
        "commit_id": reverify["commit_id"],
        "submitted_at": reverify["submitted_at"],
        "review_id": reverify["review_id"],
    }
    if reverify["state"] == "CHANGES_REQUESTED":
        case["standing_loss_at"] = reverify["submitted_at"]
        case["standing_after_reverify"] = "LOST"
    else:
        case["standing_after_reverify"] = "VALID"
    return case


def _rate(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def _med(values: list[float]) -> float | None:
    return None if not values else float(median(values))


def evaluate(
    cases: Iterable[dict[str, Any]],
    prereg: dict[str, Any],
    *,
    source_access_ok: bool = True,
) -> dict[str, Any]:
    rows = [dict(c) for c in cases]
    if not source_access_ok:
        return {
            "schema": "openline.ace.sld002.result.v1",
            "experiment_id": "SLD-002",
            "verdict": "SOURCE_ACCESS_FAILED",
            "policy_authority": "NONE",
            "runtime_permission": "NONE",
        }

    eligible = [c for c in rows if c.get("eligible")]
    terminal = [c for c in eligible if c["stratum"] == "terminal_unmerged"]
    valid_controls = [
        c for c in eligible if c.get("standing_after_reverify") == "VALID"
    ]
    detected = [
        c
        for c in terminal
        if c.get("standing_after_reverify") == "LOST"
        and c.get("standing_loss_at")
    ]
    repositories = {c["repository"] for c in eligible}

    olp_leads = [
        _hours(_ts(c["headline_at"]) - _ts(c["standing_loss_at"]))
        for c in detected
    ]
    naive_terminal_leads = [
        _hours(_ts(c["headline_at"]) - _ts(c["change"]["committed_at"]))
        for c in terminal
    ]

    ttl_hours = float(prereg["ttl_hours"])
    ttl_terminal_leads = []
    ttl_detected = 0
    for c in terminal:
        t_ttl = _ts(c["baseline_approval"]["submitted_at"]) + ttl_hours * 3600.0
        t_head = _ts(c["headline_at"])
        if t_ttl < t_head:
            ttl_detected += 1
            ttl_terminal_leads.append(_hours(t_head - t_ttl))

    # A VALID external re-verification is the control oracle: OLP must not emit LOST.
    olp_false = sum(
        c.get("standing_after_reverify") == "LOST" for c in valid_controls
    )
    # Naive Diff treats every post-approval bound-state mutation as invalidation.
    naive_false = len(valid_controls)

    ttl_false = 0
    for c in valid_controls:
        if not c.get("reverify"):
            continue
        t_ttl = (
            _ts(c["baseline_approval"]["submitted_at"]) + ttl_hours * 3600.0
        )
        if t_ttl < _ts(c["reverify"]["submitted_at"]):
            ttl_false += 1

    terminal_detection_fraction = _rate(len(detected), len(terminal))
    positive_lead_fraction = _rate(
        sum(value > 0 for value in olp_leads), len(olp_leads)
    )
    olp_false_rate = _rate(olp_false, len(valid_controls))
    naive_false_rate = _rate(naive_false, len(valid_controls))
    ttl_false_rate = _rate(ttl_false, len(valid_controls))
    ttl_detection_fraction = _rate(ttl_detected, len(terminal))

    enough = (
        len(terminal) >= int(prereg["minimum_terminal_cases"])
        and len(detected) >= int(prereg["minimum_detected_terminal_cases"])
        and len(valid_controls)
        >= int(prereg["minimum_valid_reverification_controls"])
        and len(repositories)
        >= int(prereg["minimum_repositories_with_eligible_cases"])
    )

    med_olp = _med(olp_leads)
    med_ttl = _med(ttl_terminal_leads)
    ratio_ok = (
        olp_false_rate
        <= float(prereg["naive_false_invalidation_ratio_max"])
        * naive_false_rate
    )
    ttl_dominates = (
        ttl_detection_fraction >= terminal_detection_fraction
        and med_ttl is not None
        and med_olp is not None
        and med_ttl >= med_olp
        and ttl_false_rate <= olp_false_rate
    )

    if not enough:
        verdict = "DATA_INSUFFICIENT"
    else:
        win = (
            terminal_detection_fraction
            >= float(prereg["minimum_terminal_detection_fraction"])
            and med_olp is not None
            and med_olp >= float(prereg["minimum_median_lead_hours"])
            and positive_lead_fraction
            >= float(prereg["minimum_positive_lead_fraction"])
            and ratio_ok
            and not ttl_dominates
        )
        verdict = (
            "EXTERNAL_STANDING_LOSS_LEAD_TIME_ADVANTAGE"
            if win
            else "NO_EXTERNAL_STANDING_LOSS_ADVANTAGE"
        )

    recovered = [
        c
        for c in eligible
        if c["stratum"] == "merged_control"
        and c.get("standing_after_reverify") == "LOST"
    ]
    terminal_without_loss = [c for c in terminal if c not in detected]

    return {
        "schema": "openline.ace.sld002.result.v1",
        "experiment_id": "SLD-002",
        "verdict": verdict,
        "data_boundary": prereg["data_boundary"],
        "counts": {
            "cases_total": len(rows),
            "eligible": len(eligible),
            "terminal": len(terminal),
            "terminal_detected_lost": len(detected),
            "valid_reverification_controls": len(valid_controls),
            "repositories_with_eligible_cases": len(repositories),
        },
        "olp": {
            "terminal_detection_fraction": terminal_detection_fraction,
            "detected_lead_hours": olp_leads,
            "median_detected_lead_hours": med_olp,
            "positive_lead_fraction": positive_lead_fraction,
            "unnecessary_invalidation_rate_on_valid_controls": olp_false_rate,
        },
        "naive_diff": {
            "terminal_detection_fraction": 1.0 if terminal else 0.0,
            "terminal_lead_hours": naive_terminal_leads,
            "median_terminal_lead_hours": _med(naive_terminal_leads),
            "unnecessary_invalidation_rate_on_valid_controls": naive_false_rate,
        },
        "ttl": {
            "ttl_hours": ttl_hours,
            "terminal_detection_fraction": ttl_detection_fraction,
            "detected_lead_hours": ttl_terminal_leads,
            "median_detected_lead_hours": med_ttl,
            "unnecessary_invalidation_rate_on_valid_controls": ttl_false_rate,
            "pareto_dominates_olp": ttl_dominates,
        },
        "coverage_limits": {
            "terminal_without_preclosure_loss_signal": [
                c["case_id"] for c in terminal_without_loss
            ],
            "merged_after_intermediate_loss": [
                c["case_id"] for c in recovered
            ],
            "note": (
                "Merged-after-loss cases are recovery, not false invalidations. "
                "Terminal-without-loss cases are misses for this standing signal."
            ),
        },
        "case_summaries": [
            {
                "case_id": c["case_id"],
                "repository": c["repository"],
                "stratum": c["stratum"],
                "eligible": c.get("eligible"),
                "standing_after_reverify": c.get("standing_after_reverify"),
                "standing_loss_at": c.get("standing_loss_at"),
                "headline_at": c.get("headline_at"),
            }
            for c in rows
        ],
        "claims": {
            "prediction": False,
            "technical_failure_prediction": False,
            "universal_external_advantage": False,
            "runtime_safety": False,
        },
        "policy_authority": "NONE",
        "runtime_permission": "NONE",
    }
