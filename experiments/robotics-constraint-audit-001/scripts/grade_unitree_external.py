from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path

def grade(path,min_trials=64):
    rows=[json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    by=defaultdict(list)
    for r in rows:
        if r.get('unitree_rl_gym_commit')!='276801e46c5d433564f24658bac64f254b7d2d4b': raise SystemExit('upstream pin mismatch')
        if r.get('policy_authority')!='NONE': raise SystemExit('authority escalation')
        by[r['arm']].append(bool(r['protected_boundary_violation']))
    arms=('baseline','sham','active','restoration'); counts={a:len(by[a]) for a in arms}
    if any(counts[a]<min_trials for a in arms): standing='INCOMPLETE'
    else:
        rate={a:sum(by[a])/len(by[a]) for a in arms}; delta=rate['active']-rate['sham']; rec=rate['active']-rate['restoration']
        if rate['baseline']>.05: standing='ABSTAIN_BASELINE_UNSTABLE'
        elif rate['sham']>.05: standing='ABSTAIN_SHAM_DAMAGE'
        elif delta<.40: standing='REJECTED_RITUAL'
        elif rate['restoration']>.05 or rec<.40: standing='UNRESOLVED_NO_RECOVERY'
        else: standing='SIMULATED_PHYSICAL_SEPARATION'
    rate={a:(sum(by[a])/len(by[a]) if by[a] else None) for a in arms}
    return {'standing':standing,'counts':counts,'violation_rates':rate,
            'active_minus_sham_delta':None if not by['active'] or not by['sham'] else rate['active']-rate['sham'],
            'restoration_recovery':None if not by['active'] or not by['restoration'] else rate['active']-rate['restoration'],
            'policy_authority':'NONE'}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('results'); ap.add_argument('--out'); a=ap.parse_args(); g=grade(a.results)
    text=json.dumps(g,indent=2,sort_keys=True); print(text)
    if a.out: Path(a.out).write_text(text+'\n')
if __name__=='__main__': main()
