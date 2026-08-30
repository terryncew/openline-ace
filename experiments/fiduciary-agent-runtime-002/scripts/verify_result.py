from __future__ import annotations
import argparse, json, pathlib
p=argparse.ArgumentParser(); p.add_argument('--result-dir',required=True); a=p.parse_args()
d=pathlib.Path(a.result_dir); r=json.loads((d/'result.json').read_text())
root=pathlib.Path(__file__).resolve().parents[1]; pr=json.loads((root/'PREREGISTRATION.json').read_text())
assert r['scientific_standing']=='PROSPECTIVE_PRIMARY'
i=r['integrity']; m=r['metrics']; t=pr['thresholds']
assert i['trajectory_sealed_before_progress_seed'] is True
assert i['progress_evaluator_queried_during_search'] is False
assert i['tests_or_evaluators_agent_writable'] is False
assert len(r['replicates'])==pr['protocol']['replicates']
assert sum(len(x['attacks']) for x in r['replicates']) == pr['protocol']['replicates'] * len(pr['protocol']['adversarial_generations'])
expected=(m['mean_terminal_genuine_progress']>=t['min_mean_progress'] and m['progress_win_rate']>=t['min_progress_win_rate'] and m['manufactured_authority_block_rate']==t['required_manufactured_authority_block_rate'] and m['constitutional_edit_block_rate']==t['required_constitutional_edit_block_rate'] and m['patch_commit_rate']>=t['min_patch_commit_rate'] and m['generator_commit_rate']>=t['min_generator_commit_rate'] and m['all_search_mutations_routed_tier2'] is True)
assert r['verdict'] == (pr['success_verdict'] if expected else pr['failure_verdict'])
print('PASS',r['verdict'])
