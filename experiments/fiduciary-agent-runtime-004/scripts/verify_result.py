from __future__ import annotations
import argparse, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from far004.experiment import adjudicate, saturation_measurement
p=argparse.ArgumentParser(); p.add_argument('--result-dir',required=True); a=p.parse_args()
r=json.loads((pathlib.Path(a.result_dir)/'result.json').read_text())
pr=json.loads((ROOT/'PREREGISTRATION.json').read_text())
assert r['experiment_id']=='FIDUCIARY-AGENT-RUNTIME-004'
assert r['scientific_standing']=='PROSPECTIVE_PRIMARY'
i=r['integrity']; m=r['metrics']; pconf=pr['protocol']
assert i['far003_runtime_directly_reused'] is True
assert i['runtime_fork_created'] is False
assert i['raw_patch_commit_rate_excluded_from_verdict'] is True
assert i['halt_saturated_active'] is False
assert i['trajectory_sealed_before_progress_seed'] is True
assert i['progress_evaluator_queries_during_search']==0
assert len(r['replicates'])==pconf['replicates']
re=saturation_measurement(r['replicates'],pconf['private_task_cases'])
for k in ('target_repair_coverage','opportunity_conditional_admission_rate','post_saturation_rejection_rate','objective_improvement_opportunities','admitted_improvement_opportunities','post_saturation_proposals','post_saturation_denials','trace_target_state_consistent','every_replicate_has_objective_opportunity','every_replicate_has_post_saturation_exposure'):
    assert m[k]==re[k], f'metric mismatch: {k}'
assert r['verdict']==adjudicate(pr,m,i)
print('PASS',r['verdict'])
