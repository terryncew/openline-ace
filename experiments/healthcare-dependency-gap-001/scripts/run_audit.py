from __future__ import annotations

import json
from pathlib import Path

from hsr001.audit import audit_fhir_control, audit_mimic_excerpt

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


def main() -> int:
    mimic = load("mimic_iv_demo_2_2_excerpt.json")
    fhir = load("fhir_positive_control.json")
    real = audit_mimic_excerpt(mimic)
    control = audit_fhir_control(fhir)

    result = {
        "profile": "openline.ace.healthcare-dependency-gap.result.v1",
        "experiment": "healthcare-dependency-gap-001",
        "external_dataset": "MIMIC-IV Clinical Database Demo v2.2",
        "external_arm": {
            "record_type": "real_deidentified",
            "perturbation": "synthetic_hypothetical_correction",
            "status": real.status,
            "explicit_dependents": list(real.explicit_dependents),
            "rejected_heuristics": list(real.rejected_heuristics),
        },
        "positive_control": {
            "record_type": "synthetic_fhir_r4",
            "status": control.status,
            "explicit_dependents": list(control.explicit_dependents),
        },
        "disposition": (
            "REAL_DATA_DEPENDENCY_COVERAGE_INSUFFICIENT"
            if real.status == "DEPENDENCY_COVERAGE_INSUFFICIENT"
            and control.status == "SELECTIVE_REOPENING_CAPABILITY_PASS"
            else "EXPERIMENT_FAIL"
        ),
        "implication": (
            "Do not silently retain healthcare decisions when required derivation edges are absent. "
            "Dependency maps must be explicitly supplied or independently established before selective reopening."
        ),
        "policy_authority": "NONE",
        "runtime_permission": "NONE",
    }
    out = ROOT / "evidence" / "result.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(result["disposition"])
    return 0 if result["disposition"] == "REAL_DATA_DEPENDENCY_COVERAGE_INSUFFICIENT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
