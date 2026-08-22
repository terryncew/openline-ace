import json, unittest
from pathlib import Path
from rta002.core import detect_regime, evaluate

ROOT=Path(__file__).resolve().parents[1]
P=json.loads((ROOT/"preregistration.json").read_text())

class RTA002Tests(unittest.TestCase):
    def test_thresholds_match_rta001(self):
        s=P["inherits_rta001"]["signal_dimensions"]
        self.assertEqual(s["dependency_churn"]["threshold"],.55)
        self.assertEqual(s["contradiction_rate"]["threshold"],.30)
        self.assertEqual(s["support_withdrawal_rate"]["threshold"],.25)

    def test_two_of_three_detector(self):
        r={"dependency_churn":.56,"contradiction_rate":.31,"support_withdrawal_rate":0}
        self.assertTrue(detect_regime(r,P))
        r["contradiction_rate"]=0
        self.assertFalse(detect_regime(r,P))

    def test_sparse_external_result_is_data_insufficient(self):
        rows=[{
          "case_id":i,"checkpoint":f"2026-01-{(i%28)+1:02d}T00:00:00Z",
          "age_since_last_verification":.2,"dependency_churn":0,
          "contradiction_rate":0,"support_withdrawal_rate":0,
          "later_standing_failure":False,"provenance":"external_github_review_history"
        } for i in range(10)]
        self.assertEqual(evaluate(rows,P)["verdict"],"DATA_INSUFFICIENT")

    def test_authority_never_granted(self):
        rows=[{
          "case_id":i,"checkpoint":f"2026-02-{(i%28)+1:02d}T00:00:00Z",
          "age_since_last_verification":.2,
          "dependency_churn":.8 if i%2 else .1,
          "contradiction_rate":.5 if i%2 else 0,
          "support_withdrawal_rate":0,
          "later_standing_failure":bool(i%2),
          "provenance":"external_github_review_history"
        } for i in range(48)]
        self.assertEqual(evaluate(rows,P)["policy_authority"],"NONE")

if __name__=="__main__":
    unittest.main()
