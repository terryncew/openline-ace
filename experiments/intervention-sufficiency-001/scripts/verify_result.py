from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from is001.core import audit_rows, load_policy
from is001.fixtures import global_rule_control, state_specific_control


def main() -> None:
    result_path = ROOT / "results" / "reference_result.json"
    committed = json.loads(result_path.read_text(encoding="utf-8"))
    policy = load_policy()
    expected_reports = {
        "global_rule_control": audit_rows(global_rule_control(), policy),
        "state_specific_control": audit_rows(state_specific_control(), policy),
    }
    errors: list[str] = []
    if committed.get("reports") != expected_reports:
        errors.append("reference reports do not reproduce")
    if committed.get("status") != "MECHANICS_PASS_EXTERNAL_CANDIDATE_UNRUN":
        errors.append("reference status mismatch")
    if committed.get("external_candidate_status") != "UNRUN":
        errors.append("external candidate status was promoted")
    if committed.get("policy_authority") != "NONE" or committed.get("execution_authority") != "NONE":
        errors.append("authority boundary changed")
    if expected_reports["global_rule_control"]["verdict"] != "INSUFFICIENT_INTERVENTION_CONTRAST":
        errors.append("global rule control was not rejected")
    if expected_reports["state_specific_control"]["verdict"] != "SUFFICIENT_FOR_STATE_CONDITIONED_TRANSITION_TEST":
        errors.append("state-specific control did not clear")
    print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
