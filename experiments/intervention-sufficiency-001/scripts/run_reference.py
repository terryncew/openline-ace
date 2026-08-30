from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from is001.core import audit_rows, load_policy
from is001.fixtures import global_rule_control, state_specific_control


def main() -> None:
    policy = load_policy()
    reports = {
        "global_rule_control": audit_rows(global_rule_control(), policy),
        "state_specific_control": audit_rows(state_specific_control(), policy),
    }
    expected = {
        "global_rule_control": "INSUFFICIENT_INTERVENTION_CONTRAST",
        "state_specific_control": "SUFFICIENT_FOR_STATE_CONDITIONED_TRANSITION_TEST",
    }
    mechanics_passed = all(reports[name]["verdict"] == verdict for name, verdict in expected.items())
    result = {
        "schema": "openline.ace.intervention-sufficiency.reference-result.v1",
        "experiment_id": policy["experiment_id"],
        "status": "MECHANICS_PASS_EXTERNAL_CANDIDATE_UNRUN" if mechanics_passed else "MECHANICS_FAIL",
        "mechanics_passed": mechanics_passed,
        "external_candidate_status": "UNRUN",
        "reports": reports,
        "policy_authority": "NONE",
        "execution_authority": "NONE",
    }
    out = ROOT / "results" / "reference_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if not mechanics_passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
