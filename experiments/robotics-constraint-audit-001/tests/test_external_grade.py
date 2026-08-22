import json,tempfile,unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from grade_unitree_external import grade
class T(unittest.TestCase):
    def test_external_grade_shape(self):
        rows=[]
        for arm,viol in [('baseline',0),('sham',0),('active',64),('restoration',0)]:
            for i in range(64):
                rows.append({'arm':arm,'seed':i,'protected_boundary_violation':i<viol,
                'unitree_rl_gym_commit':'276801e46c5d433564f24658bac64f254b7d2d4b','policy_authority':'NONE'})
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'r.jsonl'; p.write_text('\n'.join(json.dumps(x) for x in rows)+'\n')
            self.assertEqual(grade(p)['standing'],'SIMULATED_PHYSICAL_SEPARATION')
if __name__=='__main__': unittest.main()
