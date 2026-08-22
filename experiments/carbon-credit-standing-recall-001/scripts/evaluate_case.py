from __future__ import annotations

import json
from pathlib import Path

from ccr.replay import run_case

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    case = json.loads(
        (ROOT / "fixtures" / "vcs_2372_boeing_case.json").read_text(encoding="utf-8")
    )
    oracle = json.loads(
        (ROOT / "oracle" / "vcs_2372_oracle.json").read_text(encoding="utf-8")
    )
    methods = run_case(case, oracle)

    selective = methods["selective_reverification"]["metrics"]
    global_metrics = methods["global_invalidation"]["metrics"]
    flat = methods["flat_registry"]["metrics"]

    passed = (
        selective["missed_reopenings"] == 0
        and selective["excess_reviews"] == 0
        and selective["review_count"] < global_metrics["review_count"]
        and selective["missed_reopenings"] < flat["missed_reopenings"]
    )

    result = {
        "profile": "openline.ace.ccr001.result.v1",
        "status": "EXTERNAL_POLICY_REPLAY_PASS" if passed else "EXTERNAL_POLICY_REPLAY_FAIL",
        "case_id": case["case_id"],
        "case_type": case["case_type"],
        "methods": methods,
        "review_reduction_vs_global": round(
            1 - selective["review_count"] / global_metrics["review_count"], 6
        ),
        "recovery": {
            "event": case["recovery_event"]["artifact"],
            "restores_under_external_rule": case["recovery_event"]["restores"],
            "does_not_automatically_decide": case["recovery_event"]["does_not_automatically_decide"],
            "interpretation": "Verra says environmental integrity is considered restored if all excess credits are replaced; corporate-reporting disposition remains receiver-owned."
        },
        "claim_boundary": [
            "This is an external-policy replay over a receiver-declared dependency graph.",
            "It does not prove automatic dependency discovery or graph completeness.",
            "Reopening a downstream corporate-use claim means reverify; it does not mean the claim was false.",
            "The Verra registry/QCR policy is the standing oracle for this replay, not a universal carbon-market rule.",
            "Policy authority and runtime permission remain NONE."
        ],
        "policy_authority": "NONE",
        "runtime_permission": "NONE",
    }

    out = ROOT / "evidence" / "result.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "ccr001_external_policy_replay "
        f"status={result['status']} "
        f"selective_reviews={selective['review_count']} "
        f"global_reviews={global_metrics['review_count']} "
        f"flat_misses={flat['missed_reopenings']}"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
