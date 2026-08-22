import tempfile,unittest,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(R))
from rca001.envelope import EnvelopeConfig,stopping_distance,assess
from rca001.core import run,grade
class T(unittest.TestCase):
 def test_formula(self): self.assertAlmostEqual(stopping_distance(2,EnvelopeConfig(reaction_time_s=.1,min_deceleration_mps2=2,safety_margin_m=.2)),1.4)
 def test_fresh_commit(self): self.assertEqual(assess(speed_mps=1,distance_to_boundary_m=2,evidence_age_ms=10,trusted=True,cfg=EnvelopeConfig())["disposition"],"COMMIT")
 def test_stale_deny(self): self.assertEqual(assess(speed_mps=1,distance_to_boundary_m=2,evidence_age_ms=101,trusted=True,cfg=EnvelopeConfig())["disposition"],"DENY")
 def test_untrusted_quarantine(self): self.assertEqual(assess(speed_mps=1,distance_to_boundary_m=2,evidence_age_ms=10,trusted=False,cfg=EnvelopeConfig())["disposition"],"QUARANTINE")
 def test_outside_deny(self): self.assertEqual(assess(speed_mps=2,distance_to_boundary_m=.3,evidence_age_ms=10,trusted=True,cfg=EnvelopeConfig())["disposition"],"DENY")
 def test_four_arm(self):
  with tempfile.TemporaryDirectory() as d:
   g=grade(run(d,64)); self.assertEqual(g["standing"],"SUPPORTED_CONFORMANCE_ONLY"); self.assertEqual(g["policy_authority"],"NONE")
 def test_underpowered(self):
  with tempfile.TemporaryDirectory() as d: self.assertEqual(grade(run(d,8))["standing"],"INCOMPLETE")
if __name__=="__main__": unittest.main()
