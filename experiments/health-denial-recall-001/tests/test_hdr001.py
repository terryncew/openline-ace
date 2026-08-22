from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from hdr001.recall import (
    selective_denial_recall,
    flat_process_update,
    global_reopen,
    run,
)

RECORDS = json.loads((HERE / "fixtures" / "claims.json").read_text())
BY_ID = {r["claim_id"]: r for r in RECORDS}

class HealthDenialRecallTests(unittest.TestCase):
    def test_window_is_inclusive(self):
        self.assertEqual(selective_denial_recall(BY_ID["affected-001"]), "REOPEN_REQUIRED")
        self.assertEqual(selective_denial_recall(BY_ID["affected-002"]), "REOPEN_REQUIRED")

    def test_explicit_cap_exclusions_do_not_reopen(self):
        for rid in ["eiu-excluded", "resolved-excluded", "covid-excluded"]:
            self.assertEqual(selective_denial_recall(BY_ID[rid]), "CAP_EXCLUDED")

    def test_outside_date_window_is_outside_scope(self):
        self.assertEqual(selective_denial_recall(BY_ID["before-window"]), "OUTSIDE_CAP_SCOPE")
        self.assertEqual(selective_denial_recall(BY_ID["after-window"]), "OUTSIDE_CAP_SCOPE")

    def test_other_denial_basis_is_outside_scope(self):
        self.assertEqual(selective_denial_recall(BY_ID["other-denial-basis"]), "OUTSIDE_CAP_SCOPE")

    def test_unknown_target_population_fails_closed(self):
        self.assertEqual(
            selective_denial_recall(BY_ID["unknown-service-membership"]),
            "UNDETERMINED",
        )

    def test_flat_policy_update_misses_required_reopenings(self):
        result = run(RECORDS)
        self.assertGreater(
            result["methods"]["flat_process_update"]["metrics"]["missed_reopenings"], 0
        )

    def test_global_reopen_creates_excess(self):
        result = run(RECORDS)
        self.assertGreater(
            result["methods"]["global_reopen"]["metrics"]["excess_reopenings"], 0
        )

    def test_selective_recall_matches_frozen_oracle(self):
        result = run(RECORDS)
        m = result["methods"]["selective_denial_recall"]["metrics"]
        self.assertEqual(m["missed_reopenings"], 0)
        self.assertEqual(m["excess_reopenings"], 0)
        self.assertEqual(result["status"], "EXTERNAL_REGULATORY_RECALL_PASS")

    def test_no_patient_specific_authority(self):
        result = run(RECORDS)
        self.assertEqual(result["policy_authority"], "NONE")
        self.assertEqual(result["runtime_permission"], "NONE")
        self.assertEqual(result["patient_specific_advice"], "NONE")

if __name__ == "__main__":
    unittest.main()
