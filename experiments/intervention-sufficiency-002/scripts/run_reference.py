from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from is002.core import audit_rows, load_policy
from is002.fixtures import (
    deterministic_global_control,
    deterministic_state_specific_control,
    stochastic_state_specific_control,
    validated_model_state_specific_control,
)


def main() -> None:
    policy = load_policy()
    external_path = ROOT / "results" / "unitree_external_result.json"
    external = json.loads(external_path.read_text(encoding="utf-8"))
    result = {
        "schema": "openline.ace.intervention-sufficiency.reference-result.v2",
        "experiment_id": policy["experiment_id"],
        "status": "MECHANICS_PASS_UNITREE_EXTERNAL_FROZEN",
        "policy_authority": "NONE",
        "execution_authority": "NONE",
        "external_candidate_status": "COMPLETE_RETROSPECTIVE_REPLAY",
        "external_verdict": external["verdict"],
        "external_result_sha256": hashlib.sha256(
            external_path.read_bytes()
        ).hexdigest(),
        "reports": {
            "deterministic_global_control": audit_rows(
                deterministic_global_control(), policy
            ),
            "deterministic_state_specific_control": audit_rows(
                deterministic_state_specific_control(), policy
            ),
            "stochastic_state_specific_control": audit_rows(
                stochastic_state_specific_control(), policy
            ),
            "validated_model_state_specific_control": audit_rows(
                validated_model_state_specific_control(), policy
            ),
        },
    }
    output = ROOT / "results" / "reference_result.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
