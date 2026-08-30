import json, unittest
from pathlib import Path
from is003.grid import load_grid, verify_grid, pilot_tuples, context_tuple
from is003.audit import audit, ACTIONS, LAGS
ROOT=Path(__file__).resolve().parents[1]
class TestIS003(unittest.TestCase):
    def test_grid_is_exact_and_disjoint(self):
        g=load_grid(); self.assertEqual([],verify_grid(g)); self.assertFalse(set(map(context_tuple,g['contexts'])) & pilot_tuples())
    def test_prereg_binds_grid(self):
        import hashlib
        p=json.loads((ROOT/'PREREGISTRATION.json').read_text()); self.assertEqual(p['grid_sha256'],hashlib.sha256((ROOT/'GRID.json').read_bytes()).hexdigest()); self.assertEqual(p['pilot_use'],'DESIGN_ONLY_NO_OUTCOMES_IN_EVIDENCE_OR_THRESHOLDS')
    def test_audit_rejects_global_remedy(self):
        rows=[]
        for c in load_grid()['contexts']:
            risk=f"force:{c['push_force_newtons']:g}|abs_pitch_torque:{abs(c['push_pitch_torque_magnitude_nm']):g}"
            for a in ACTIONS:
                for l in LAGS:
                    rows.append({'context_id':c['context_id'],'action_id':a,'lag_ms':l,'outcome_success':a=='STOP','apparent_risk_bucket':risk,'policy_authority':'NONE'})
        r=audit(rows); self.assertEqual('CONFIRMATORY_INTERVENTION_CONTRAST_FAILED',r['verdict']); self.assertFalse(r['gates']['global_action_delay_cell_accuracy']['passed'])

    def test_audit_accepts_strong_state_specific_contrast(self):
        rows=[]
        contexts=load_grid()['contexts']
        for i,c in enumerate(contexts):
            risk=f"pair:{i//2}"
            for ai,a in enumerate(ACTIONS):
                for l in LAGS:
                    preferred=((i+ai)%2)==0
                    success=preferred and l<160
                    rows.append({'context_id':c['context_id'],'action_id':a,'lag_ms':l,'outcome_success':success,'apparent_risk_bucket':risk,'policy_authority':'NONE'})
        r=audit(rows)
        self.assertEqual('CONFIRMED_STATE_SPECIFIC_INTERVENTION_CONTRAST',r['verdict'])
        self.assertTrue(r['transition_benchmark_authorized'])
        self.assertLessEqual(r['metrics']['global_action_delay_cell_accuracy'],0.85)

    def test_authority_contamination_invalidates(self):
        r=audit([{'context_id':'x','action_id':'STOP','lag_ms':0,'outcome_success':True,'apparent_risk_bucket':'x','policy_authority':'SELECT'}]); self.assertEqual('INVALID_CONFIRMATORY_CORPUS',r['verdict'])
if __name__=='__main__': unittest.main()
