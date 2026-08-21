import unittest

from aca001.conformance import run_conformance


class ConformanceTests(unittest.TestCase):
    def test_expected_separation(self):
        result = run_conformance()
        self.assertEqual(result["verdict"], "CONFORMANCE_PASS_EXTERNAL_UNRUN")
        self.assertEqual(
            result["observed_standings"]["validated-artifact-binding"],
            "SUPPORTED",
        )
        self.assertEqual(
            result["observed_standings"]["format-scratchpad-ritual"],
            "REJECTED_RITUAL",
        )
        self.assertEqual(
            result["observed_standings"]["generic-context-disturbance"],
            "UNDECIDABLE_SHAM_EFFECT",
        )
        self.assertEqual(
            result["observed_standings"]["wrapper-audit-marker-rule"],
            "REJECTED_RITUAL",
        )

    def test_external_lane_remains_unrun(self):
        result = run_conformance()
        self.assertEqual(result["blind_external_lane"], "UNRUN")
        self.assertEqual(
            result["scientific_standing"],
            "MECHANICS_ONLY_NOT_EXTERNAL_AGENT_EVIDENCE",
        )


if __name__ == "__main__":
    unittest.main()
