
import json,unittest
from pathlib import Path
from rta003.core import detect_regime,evaluate
R=Path(__file__).resolve().parents[1]; P=json.loads((R/"preregistration.json").read_text())
class T(unittest.TestCase):
 def test_frozen_thresholds(self):
  s=P["inherits_frozen_rta001"]["signal_dimensions"]
  self.assertEqual([s[x]["threshold"] for x in ["dependency_churn","contradiction_rate","support_withdrawal_rate"]],[.55,.30,.25])
 def test_two_of_three(self):
  self.assertTrue(detect_regime({"dependency_churn":.6,"contradiction_rate":.4,"support_withdrawal_rate":0},P))
 def test_sparse_is_terminal_insufficient(self):
  rows=[{"repository":"x/y","case_id":i,"checkpoint":f"2025-01-{i%28+1:02}T00:00:00Z","age_since_last_verification":.1,
  "dependency_churn":0,"contradiction_rate":0,"support_withdrawal_rate":0,"later_standing_failure":False} for i in range(20)]
  self.assertEqual(evaluate(rows,P)["verdict"],"DATA_INSUFFICIENT")
 def test_authority_none(self):
  self.assertEqual(evaluate([],P)["policy_authority"],"NONE")
if __name__=="__main__": unittest.main()
