from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def impacts(result, scenario):
    return {
        item["claim_id"]: item["disposition"]
        for item in result["scenarios"][scenario]["claim_impacts"]
    }


def main() -> int:
    result = json.loads(
        (ROOT / "evidence" / "result.json").read_text(encoding="utf-8")
    )

    assert result["status"] == "VERIFIED_CONTINUITY_CONFORMANCE_PASS"
    assert result["policy_authority"] == "NONE"
    assert result["runtime_permission"] == "NONE"
    assert result["display_scalar_authoritative"] is False

    readme = impacts(result, "readme_only")
    assert readme["docs-reviewed"] == "REOPEN"
    assert readme["merge-current-patch"] == "RETAIN"

    patch = impacts(result, "patch_rebind")
    assert patch["merge-current-patch"] == "REOPEN"
    assert patch["docs-reviewed"] == "RETAIN"

    sensor = impacts(result, "sensor_large")
    assert sensor["control-stable"] == "REOPEN"
    assert sensor["telemetry-safe"] == "ACE_RECOMMENDED"
    assert result["scenarios"]["sensor_large"]["saturated_dimensions"] == [
        "sensor_bias_micros"
    ]

    assert (
        result["successor_baseline"]["parent_receipt_id"]
        == result["baseline"]["receipt_id"]
    )
    print("drift_observer_evidence_verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
