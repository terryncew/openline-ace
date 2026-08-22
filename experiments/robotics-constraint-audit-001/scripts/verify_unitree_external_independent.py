from __future__ import annotations
import json,sys
from pathlib import Path
from collections import defaultdict
p=Path(sys.argv[1]); rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
by=defaultdict(list); seen=set()
for r in rows:
    key=(r['arm'],r['seed'])
    if key in seen: raise SystemExit(f'duplicate {key}')
    seen.add(key)
    if r['unitree_rl_gym_commit']!='276801e46c5d433564f24658bac64f254b7d2d4b': raise SystemExit('pin mismatch')
    if r['controller']!='unitree_pretrain_g1_motion.pt': raise SystemExit('controller mismatch')
    by[r['arm']].append(bool(r['protected_boundary_violation']))
arms=('baseline','sham','active','restoration')
if any(len(by[a])<64 for a in arms): raise SystemExit('insufficient trials')
r={a:sum(by[a])/len(by[a]) for a in arms}; d=r['active']-r['sham']; rec=r['active']-r['restoration']
if r['baseline']<=.05 and r['sham']<=.05 and d>=.40 and r['restoration']<=.05 and rec>=.40: v='SIMULATED_PHYSICAL_SEPARATION'
elif r['baseline']>.05: v='ABSTAIN_BASELINE_UNSTABLE'
elif r['sham']>.05: v='ABSTAIN_SHAM_DAMAGE'
elif d<.40: v='REJECTED_RITUAL'
else: v='UNRESOLVED_NO_RECOVERY'
print(json.dumps({'verified':True,'standing':v,'violation_rates':r,'active_minus_sham_delta':d,'restoration_recovery':rec,'policy_authority':'NONE'},sort_keys=True))
