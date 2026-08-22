from __future__ import annotations

import json
import unittest
from pathlib import Path

from hsr001.audit import audit_fhir_control, audit_mimic_excerpt

ROOT = Path(__file__).resolve().parents[1]


class HealthcareDependencyGapTests(unittest.TestCase):
    def load(self, name):
        return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))

    def test_real_mimic_record_fails_closed_on_missing_dependency(self):
        result = audit_mimic_excerpt(self.load("mimic_iv_demo_2_2_excerpt.json"))
        self.assertEqual(result.status, "DEPENDENCY_COVERAGE_INSUFFICIENT")
        self.assertEqual(result.explicit_dependents, ())

    def test_same_hospitalization_is_not_promoted_to_dependency(self):
        result = audit_mimic_excerpt(self.load("mimic_iv_demo_2_2_excerpt.json"))
        self.assertIn("same_hospitalization", result.rejected_heuristics)

    def test_temporal_proximity_is_not_promoted_to_dependency(self):
        result = audit_mimic_excerpt(self.load("mimic_iv_demo_2_2_excerpt.json"))
        self.assertIn("temporal_proximity", result.rejected_heuristics)

    def test_fhir_explicit_reference_reopens_only_dependent_request(self):
        result = audit_fhir_control(self.load("fhir_positive_control.json"))
        self.assertEqual(result.status, "SELECTIVE_REOPENING_CAPABILITY_PASS")
        self.assertEqual(result.explicit_dependents, ("potassium-replacement-dependent",))

    def test_unrelated_fhir_request_retains_by_absence_of_explicit_edge(self):
        result = audit_fhir_control(self.load("fhir_positive_control.json"))
        self.assertNotIn("unrelated-independent-medication", result.explicit_dependents)


if __name__ == "__main__":
    unittest.main()
