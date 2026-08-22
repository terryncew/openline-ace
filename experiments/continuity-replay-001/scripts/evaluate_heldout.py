from __future__ import annotations
import hashlib, json
from pathlib import Path
from continuity_replay.replay import evaluate_case
ROOT = Path(__file__).resolve().parents[1]

def aggregate(rows, method):
    review=true=excess=missed=0
    for row in rows:
        m=row["methods"][method]["metrics"]
        review+=int(m["review_count"]); true+=int(m["true_reopenings"]); excess+=int(m["excess_reviews"]); missed+=int(m["missed_reopenings"])
    warranted=true+missed
    precision=1.0 if review==0 else true/review
    recall=1.0 if warranted==0 else true/warranted
    f1=0.0 if precision+recall==0 else 2*precision*recall/(precision+recall)
    return {"review_count":review,"true_reopenings":true,"excess_reviews":excess,"missed_reopenings":missed,"precision":round(precision,6),"recall":round(recall,6),"f1":round(f1,6)}

def main() -> int:
    corpus=json.loads((ROOT/'heldout'/'corpus.json').read_text()); oracle=json.loads((ROOT/'heldout'/'oracle.json').read_text())
    rows=[]
    for case in corpus['cases']:
        cid=case['case_id']; warranted=frozenset(oracle['cases'][cid]['warranted_reopenings'])
        rows.append({'case_id':cid,'repository':case['repository'],'base_commit':case['base_commit'],'head_commit':case['head_commit'],'methods':evaluate_case(case,warranted)})
    methods=tuple(rows[0]['methods']); agg={name:aggregate(rows,name) for name in methods}
    obs=agg['continuity_observer']; glob=agg['global_invalidation']; flat=agg['flat_latest_state']
    if obs['missed_reopenings']!=0: verdict='FAIL_MISSED_WARRANTED_REOPENING'
    elif obs['excess_reviews']!=0: verdict='FAIL_EXCESS_REOPENING'
    elif glob['review_count']<=obs['review_count']: verdict='FAIL_NO_REVIEW_SAVINGS'
    elif flat['missed_reopenings']<=obs['missed_reopenings']: verdict='FAIL_NO_RECALL_ADVANTAGE'
    else: verdict='SELECTIVE_REOPENING_HELDOUT_PASS'
    result={'profile':'openline.ace.continuity-replay.result.v1','status':verdict,'case_count':len(rows),'claim_count':sum(len(c['graph']['claims']) for c in corpus['cases']),'heldout_repositories':[c['repository'] for c in corpus['cases']],'engine_bundle_sha256':corpus['engine_bundle_sha256'],'aggregate':agg,'review_reduction_vs_global':round(1.0-obs['review_count']/glob['review_count'],6),'policy_authority':'NONE','runtime_permission':'NONE','claim_boundary':['Held-out replay tests selective reopening over frozen dependency declarations.','It does not prove automatic dependency discovery.','It does not prove the dependency graph is complete.','The two external histories are a first replay corpus, not a population estimate.','State displacement is not interpreted as truth, safety, or permission.'],'cases':rows}
    (ROOT/'evidence'/'result.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    digest=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
    receipt={'profile':'openline.ace.continuity-replay.receipt.v1','result_sha256':digest,'status':verdict,'policy_authority':'NONE','runtime_permission':'NONE'}
    (ROOT/'evidence'/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print('CONTINUITY REPLAY 001'); print('verdict:',verdict)
    for name,m in agg.items(): print(name,'reviews='+str(m['review_count']),'missed='+str(m['missed_reopenings']),'excess='+str(m['excess_reviews']),'precision='+str(m['precision']),'recall='+str(m['recall']))
    print('review_reduction_vs_global:',result['review_reduction_vs_global'])
    return 0 if verdict=='SELECTIVE_REOPENING_HELDOUT_PASS' else 1
if __name__=='__main__': raise SystemExit(main())
