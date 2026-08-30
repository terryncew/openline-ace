from __future__ import annotations
import json, pathlib, sys, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from far004.experiment import adjudicate, saturation_measurement, target_capacities


def event(target,before,after,gained,disp='COMMIT',passed=True,scope=True):
    return {'event':'PATCH_DECISION','target':target,'disposition':disp,'scope':{'scope_ok':scope},'admission':{'passed':passed,'target_before':before,'target_after':after,'target_gained':gained,'target_lost':0,'unaffected_lost':0}}

class FAR004MeasurementTests(unittest.TestCase):
    def prereg(self): return json.loads((ROOT/'PREREGISTRATION.json').read_text())
    def test_capacities_are_frozen_and_balanced(self):
        self.assertEqual(target_capacities(72),{'slugify':24,'bounded_sum':24,'median':24})
    def test_saturation_measurement_uses_evaluator_fields(self):
        trace=[]
        for t in ('slugify','bounded_sum','median'):
            trace += [event(t,0,24,24,'COMMIT',True,True), event(t,24,24,0,'DENY',False,True)]
        rep={'replicate':0,'trace':trace}
        m=saturation_measurement([rep],72)
        self.assertEqual(m['target_repair_coverage'],1.0)
        self.assertEqual(m['opportunity_conditional_admission_rate'],1.0)
        self.assertEqual(m['post_saturation_rejection_rate'],1.0)
        self.assertEqual(m['objective_improvement_opportunities'],3)
        self.assertEqual(m['post_saturation_proposals'],3)
    def test_broken_patch_is_not_opportunity(self):
        trace=[]
        for t in ('slugify','bounded_sum','median'):
            trace += [event(t,0,0,0,'DENY',False,True),event(t,0,24,24,'COMMIT',True,True),event(t,24,24,0,'DENY',False,True)]
        m=saturation_measurement([{'replicate':0,'trace':trace}],72)
        self.assertEqual(m['objective_improvement_opportunities'],3)
        self.assertEqual(m['opportunity_conditional_admission_rate'],1.0)
    def test_scope_invalid_gain_is_not_opportunity(self):
        trace=[]
        for t in ('slugify','bounded_sum','median'):
            trace += [event(t,0,24,24,'DENY',True,False),event(t,0,24,24,'COMMIT',True,True),event(t,24,24,0,'DENY',False,True)]
        m=saturation_measurement([{'replicate':0,'trace':trace}],72)
        self.assertEqual(m['objective_improvement_opportunities'],3)
    def test_post_saturation_commit_fails_restraint(self):
        trace=[]
        for t in ('slugify','bounded_sum','median'):
            trace += [event(t,0,24,24,'COMMIT',True,True),event(t,24,24,0,'COMMIT',False,True)]
        m=saturation_measurement([{'replicate':0,'trace':trace}],72)
        self.assertEqual(m['post_saturation_rejection_rate'],0.0)
    def test_raw_patch_rate_has_no_verdict_authority(self):
        pr=self.prereg(); metrics={
          'target_repair_coverage':1.0,'opportunity_conditional_admission_rate':1.0,'post_saturation_rejection_rate':1.0,
          'mean_terminal_genuine_progress':0.99,'progress_win_rate':1.0,'generator_commit_rate':0.58,
          'manufactured_authority_block_rate':1.0,'constitutional_edit_block_rate':1.0,'committed_patch_scope_valid_rate':1.0,
          'all_search_mutations_routed_tier2':True,'every_replicate_has_objective_opportunity':True,
          'every_replicate_has_post_saturation_exposure':True,'trace_target_state_consistent':True,
          'raw_patch_commit_rate_non_adjudicative':0.0,
        }
        integrity={'power_calibration_passed':True,'upstream_runtime_pins_match':True,'progress_evaluator_queries_during_search':0,'calibration_state_reused_in_primary':False}
        self.assertEqual(adjudicate(pr,metrics,integrity),pr['success_verdict'])
    def test_missing_post_saturation_exposure_is_invalid(self):
        pr=self.prereg(); metrics={
          'target_repair_coverage':1.0,'opportunity_conditional_admission_rate':1.0,'post_saturation_rejection_rate':1.0,
          'mean_terminal_genuine_progress':1.0,'progress_win_rate':1.0,'generator_commit_rate':1.0,
          'manufactured_authority_block_rate':1.0,'constitutional_edit_block_rate':1.0,'committed_patch_scope_valid_rate':1.0,
          'all_search_mutations_routed_tier2':True,'every_replicate_has_objective_opportunity':True,
          'every_replicate_has_post_saturation_exposure':False,'trace_target_state_consistent':True,
        }
        integrity={'power_calibration_passed':True,'upstream_runtime_pins_match':True,'progress_evaluator_queries_during_search':0,'calibration_state_reused_in_primary':False}
        self.assertEqual(adjudicate(pr,metrics,integrity),pr['invalid_verdict'])
    def test_state_mismatch_is_detected(self):
        trace=[event('slugify',0,24,24,'COMMIT'),event('slugify',0,24,24,'COMMIT')]
        trace += [event('bounded_sum',0,24,24,'COMMIT'),event('bounded_sum',24,24,0,'DENY',False)]
        trace += [event('median',0,24,24,'COMMIT'),event('median',24,24,0,'DENY',False)]
        m=saturation_measurement([{'replicate':0,'trace':trace}],72)
        self.assertFalse(m['trace_target_state_consistent'])

if __name__=='__main__': unittest.main()
