import unittest

from aca001.conformance import observational_summary, observational_trace_rows


class ObservationalFixtureTests(unittest.TestCase):
    def test_true_and_ritual_are_observationally_indistinguishable(self):
        summary = observational_summary(observational_trace_rows())
        self.assertEqual(summary["validated_artifact_binding_prevalence_among_success"], 1.0)
        self.assertEqual(summary["format_scratchpad_prevalence_among_success"], 1.0)


if __name__ == "__main__":
    unittest.main()
