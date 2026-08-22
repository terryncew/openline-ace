import json,unittest
from pathlib import Path
from rta001.core import detect_regime,evaluate
ROOT=Path(__file__).resolve().parents[1]; P=json.loads((ROOT/"preregistration.json").read_text()); ROWS=[json.loads(x) for x in (ROOT/"fixture.jsonl").read_text().splitlines() if x.strip()]
class T(unittest.TestCase):
 def test_two_of_three(self):
  r=dict(ROWS[0]); r.update(dependency_churn=.56,contradiction_rate=.31,support_withdrawal_rate=0); self.assertTrue(detect_regime(r,P)); r["contradiction_rate"]=0; self.assertFalse(detect_regime(r,P))
 def test_no_authority(self):
  o=evaluate(ROWS,P); self.assertEqual(o["policy_authority"],"NONE"); self.assertFalse(o["claims"]["grants_execution_authority"])
 def test_synthetic_ceiling(self):
  o=evaluate(ROWS,P); self.assertNotEqual(o["verdict"],"PREDICTIVE_ADVANTAGE_CANDIDATE"); self.assertFalse(o["claims"]["external_predictive_value_established"])
 def test_half_life_forbidden(self): self.assertIn("standing_has_a_universal_half_life",P["forbidden_claims"])
if __name__=="__main__": unittest.main()
