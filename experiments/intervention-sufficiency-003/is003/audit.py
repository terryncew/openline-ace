from __future__ import annotations
from collections import Counter, defaultdict
import itertools, json
from pathlib import Path

ACTIONS=['CONTINUE','LATERAL_LEFT','LATERAL_RIGHT','RETREAT','SLOW','STOP']
LAGS=[0,40,80,120,160]

def load_policy(path=None):
    path=Path(path) if path else Path(__file__).resolve().parents[1]/'PREREGISTRATION.json'
    return json.loads(path.read_text())

def _gate(observed, relation, required):
    ok = observed==required if relation=='==' else observed>=required if relation=='>=' else observed<=required
    return {'passed':bool(ok),'observed':observed,'relation':relation,'required':required}

def audit(rows, policy=None):
    policy=policy or load_policy(); th=policy['thresholds']; errors=[]
    contexts=sorted({str(r.get('context_id','')) for r in rows if r.get('context_id')})
    actions=sorted({str(r.get('action_id','')) for r in rows}); lags=sorted({int(r.get('lag_ms',-1)) for r in rows})
    if any(r.get('policy_authority')!='NONE' for r in rows): errors.append('policy_authority must be NONE')
    keys=[(r.get('context_id'),r.get('action_id'),r.get('lag_ms')) for r in rows]
    if len(set(keys))!=len(keys): errors.append('duplicate context/action/lag cell')
    if errors:
        return {'schema':'openline.ace.is003.result.v1','experiment_id':'IS-003','verdict':policy['invalid_verdict'],'errors':errors,'policy_authority':'NONE','execution_authority':'NONE'}
    by={(str(r['context_id']),str(r['action_id']),int(r['lag_ms'])): bool(r['outcome_success']) for r in rows}
    risk={str(r['context_id']):str(r['apparent_risk_bucket']) for r in rows}
    complete=sum(all((c,a,l) in by for a in ACTIONS for l in LAGS) for c in contexts)
    complete_rate=complete/len(contexts) if contexts else 0.0
    state_dep=0; global_correct=0; global_total=0
    for a in ACTIONS:
        for l in LAGS:
            vals=[by[(c,a,l)] for c in contexts if (c,a,l) in by]
            if len(set(vals))==2: state_dep+=1
            if vals:
                counts=Counter(vals); global_correct+=max(counts.values()); global_total+=len(vals)
    global_acc=global_correct/global_total if global_total else 1.0
    byrisk=defaultdict(list)
    for c in contexts: byrisk[risk[c]].append(c)
    pairs=set(); paired=set()
    for bucket,cs in byrisk.items():
        for x,y in itertools.combinations(sorted(cs),2):
            for l in LAGS:
                xs={a for a in ACTIONS if by.get((x,a,l)) is True}; ys={a for a in ACTIONS if by.get((y,a,l)) is True}
                if xs-ys and ys-xs:
                    pairs.add((x,y)); paired.update((x,y)); break
    contractions=[]
    for c in contexts:
        for a in ACTIONS:
            seq=[by.get((c,a,l)) for l in LAGS]
            for j in range(1,len(seq)):
                if seq[j] is False and any(v is True for v in seq[:j]) and not any(v is True for v in seq[j+1:]):
                    contractions.append((c,a)); break
    gates={
      'contexts':_gate(len(contexts),'==',th['required_contexts']), 'cells':_gate(len(rows),'==',th['required_cells']),
      'actions':_gate(actions,'==',ACTIONS),'lags':_gate(lags,'==',LAGS),
      'complete_context_rate':_gate(complete_rate,'>=',th['min_complete_context_rate']),
      'state_dependent_action_lag_strata':_gate(state_dep,'>=',th['min_state_dependent_action_lag_strata']),
      'bidirectional_remedy_divergent_risk_pairs':_gate(len(pairs),'>=',th['min_bidirectional_remedy_divergent_risk_pairs']),
      'contexts_in_divergent_pairs':_gate(len(paired),'>=',th['min_contexts_in_divergent_pairs']),
      'lag_contractions':_gate(len(contractions),'>=',th['min_lag_contractions']),
      'global_action_delay_cell_accuracy':_gate(global_acc,'<=',th['max_global_action_delay_cell_accuracy'])}
    passed=all(g['passed'] for g in gates.values())
    return {'schema':'openline.ace.is003.result.v1','experiment_id':'IS-003','verdict':policy['success_verdict'] if passed else policy['failure_verdict'],
            'scientific_standing':'PROSPECTIVE_CONFIRMATORY','gates':gates,'metrics':{'contexts':len(contexts),'cells':len(rows),'state_dependent_strata':state_dep,'divergent_pairs':len(pairs),'paired_contexts':len(paired),'lag_contractions':len(contractions),'global_action_delay_cell_accuracy':global_acc},
            'pilot_outcomes_used':False,'policy_authority':'NONE','execution_authority':'NONE','transition_benchmark_authorized':bool(passed)}
