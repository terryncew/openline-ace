from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def main():
    result=json.loads((ROOT/'evidence'/'result.json').read_text()); receipt=json.loads((ROOT/'evidence'/'receipt.json').read_text())
    assert receipt['result_sha256']==hashlib.sha256(canonical(result)).hexdigest()
    assert result['status']=='SELECTIVE_REOPENING_HELDOUT_PASS'
    assert result['aggregate']['continuity_observer']['missed_reopenings']==0
    assert result['aggregate']['continuity_observer']['excess_reviews']==0
    assert result['aggregate']['global_invalidation']['excess_reviews']>0
    assert result['aggregate']['flat_latest_state']['missed_reopenings']>0
    assert result['policy_authority']=='NONE' and result['runtime_permission']=='NONE'
    print('continuity_replay_evidence_verified'); return 0
if __name__=='__main__': raise SystemExit(main())
