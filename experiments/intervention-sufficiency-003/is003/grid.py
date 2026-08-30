from __future__ import annotations
import hashlib, itertools, json, random
from pathlib import Path

PHASES=[0.0,0.04,0.08,0.12,0.16]
FORCES=[120.0,180.0,240.0,320.0,420.0]
TORQUES=[0.0,15.0,30.0,45.0]
DIRECTIONS=[(1.0,0.0),(-1.0,0.0),(0.0,1.0),(0.0,-1.0),(0.70710678,0.70710678),(0.70710678,-0.70710678),(-0.70710678,0.70710678),(-0.70710678,-0.70710678)]
PILOT_SEED=20260829
SALT='IS003-CONFIRMATORY-GRID-v1'


def pilot_tuples():
    rng=random.Random(PILOT_SEED); out=set()
    for i in range(50):
        phase=PHASES[i%len(PHASES)]; force=rng.choice(FORCES); torque=rng.choice(TORQUES); dx,dy=rng.choice(DIRECTIONS); sign=-1.0 if i%2 else 1.0
        out.add((phase,force,torque,dx,dy,sign))
    return out


def context_tuple(c):
    return (float(c['phase_offset_seconds']),float(c['push_force_newtons']),float(c['push_pitch_torque_magnitude_nm']),float(c['push_direction_x']),float(c['push_direction_y']),float(c['push_pitch_torque_sign']))


def classify(force,torque):
    if force in (120.0,180.0) and torque in (0.0,15.0): return 'clean_control'
    if force in (240.0,320.0) and torque in (0.0,15.0,30.0): return 'recovery_candidate'
    if force in (320.0,420.0) and torque in (30.0,45.0): return 'adversarial'
    return None


def rank_tuple(t):
    return hashlib.sha256((SALT+'|'+json.dumps(t,separators=(',',':'))).encode()).hexdigest()


def regenerate_contexts():
    pilot=pilot_tuples(); cand=[]
    for phase,force,torque,direction,sign in itertools.product(PHASES,FORCES,TORQUES,DIRECTIONS,[1.0,-1.0]):
        dx,dy=direction; t=(phase,force,torque,dx,dy,sign)
        if t in pilot: continue
        stratum=classify(force,torque)
        if stratum: cand.append((rank_tuple(t),stratum,t))
    selected=[]
    for stratum,count in [('adversarial',40),('clean_control',30),('recovery_candidate',30)]:
        ranked=sorted(x for x in cand if x[1]==stratum)[:count]
        train_n=int(count*0.60); validation_n=int(count*0.20)
        for j,item in enumerate(ranked):
            split='train' if j<train_n else 'validation' if j<train_n+validation_n else 'test'
            selected.append((*item,split))
    selected.sort(key=lambda x:x[0])
    out=[]
    for i,(rank,stratum,t,split) in enumerate(selected):
        phase,force,torque,dx,dy,sign=t
        out.append({'context_id':f'is003-g1-{i:03d}','split':split,'stratum':stratum,'rank_sha256':rank,'phase_offset_seconds':phase,'push_force_newtons':force,'push_direction_x':dx,'push_direction_y':dy,'push_pitch_torque_magnitude_nm':torque,'push_pitch_torque_sign':sign})
    return out


def load_grid(path=None):
    path=Path(path) if path else Path(__file__).resolve().parents[1]/'GRID.json'
    return json.loads(path.read_text())


def verify_grid(grid):
    contexts=grid['contexts']; errors=[]
    if len(contexts)!=100: errors.append(f'expected 100 contexts, got {len(contexts)}')
    tuples=[context_tuple(c) for c in contexts]
    if len(set(tuples))!=len(tuples): errors.append('duplicate context tuple')
    overlap=set(tuples)&pilot_tuples()
    if overlap: errors.append(f'pilot overlap: {len(overlap)}')
    if contexts!=regenerate_contexts(): errors.append('GRID.json differs from deterministic regeneration')
    counts={k:sum(c['stratum']==k for c in contexts) for k in ('adversarial','clean_control','recovery_candidate')}
    if counts!={'adversarial':40,'clean_control':30,'recovery_candidate':30}: errors.append(f'bad strata {counts}')
    splits={k:sum(c['split']==k for c in contexts) for k in ('train','validation','test')}
    if splits!={'train':60,'validation':20,'test':20}: errors.append(f'bad splits {splits}')
    expected={'train':{'adversarial':24,'clean_control':18,'recovery_candidate':18},'validation':{'adversarial':8,'clean_control':6,'recovery_candidate':6},'test':{'adversarial':8,'clean_control':6,'recovery_candidate':6}}
    actual={split:{st:sum(c['split']==split and c['stratum']==st for c in contexts) for st in ('adversarial','clean_control','recovery_candidate')} for split in ('train','validation','test')}
    if actual!=expected: errors.append(f'bad split strata {actual}')
    return errors
