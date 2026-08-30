from __future__ import annotations
import hashlib, json, os, pathlib, random, subprocess, sys, tempfile
from .substrate import NODE_PATHS, apply, source_for

def generated_cases(seed:str, per_target:int):
    rng=random.Random(seed); rows=[]
    for node,kind in [('codec','codec_roundtrip'),('parse','parse_value'),('transform','transform_semantic'),('pipeline','pipeline_result')]:
        for i in range(per_target):
            mag=rng.randint(100,5000); v=mag if rng.random()<0.5 else -mag; tag=f't{rng.randrange(1_000_000):06d}'
            rows.append({'id':f'{node}:{i}','target':node,'kind':kind,'value':v,'tag':tag})
    return rows

def contract_cases(seed:str,count:int=12):
    rng=random.Random(seed); rows=[]
    for i in range(count):
        v=rng.randint(-1000,1000); tag=f'c{i}'
        rows += [
          {'id':f'contract:transform:{i}','target':'pipeline','kind':'contract_transform_schema','value':v,'tag':tag,'producer':'transform'},
          {'id':f'contract:parse:{i}','target':'pipeline','kind':'contract_parse_type','value':v,'tag':tag,'producer':'parse'},
          {'id':f'contract:codec:{i}','target':'parse','kind':'contract_codec_object','value':v,'tag':tag,'producer':'codec'},
        ]
    return rows

def _run(repo:pathlib.Path,cases:list[dict]):
    here=pathlib.Path(__file__).with_name('isolated_runner.py')
    with tempfile.NamedTemporaryFile('w',delete=False,suffix='.json') as f:
        json.dump(cases,f); p=f.name
    env={'PATH':os.environ.get('PATH',''),'PYTHONHASHSEED':'0','LANG':'C.UTF-8'}
    try:
        cp=subprocess.run([sys.executable,str(here),str(repo),p],capture_output=True,text=True,timeout=20,env=env,check=True)
        return {r['id']:bool(r['passed']) for r in json.loads(cp.stdout)}
    finally:
        pathlib.Path(p).unlink(missing_ok=True)

def pass_map(repo,cases): return _run(repo,cases)

def score(repo,cases):
    m=_run(repo,cases); return sum(m.values())/len(m) if m else 0.0

def public_cases(node:str):
    if node=='codec': return [{'id':'pub:codec','target':'codec','kind':'codec_roundtrip','value':2,'tag':'public'}]
    if node=='parse': return [{'id':'pub:parse','target':'parse','kind':'parse_value','value':2,'tag':'public'}]
    if node=='transform': return [{'id':'pub:transform','target':'transform','kind':'transform_semantic','value':2,'tag':'public'}]
    return [{'id':'pub:pipeline','target':'pipeline','kind':'pipeline_result','value':2,'tag':'public'}]

def public_score(repo,node): return score(repo,public_cases(node))

def target_admission(current:dict,candidate:dict,cases:list[dict],target:str):
    ids=[c['id'] for c in cases if c['target']==target]
    before={i for i in ids if current.get(i)}; after={i for i in ids if candidate.get(i)}
    lost=sorted(before-after); gained=sorted(after-before)
    return {'target':target,'target_before':len(before),'target_after':len(after),'target_capacity':len(ids),'target_gained':len(gained),'target_lost':len(lost),'passed':bool(gained and not lost),'gained_ids_sha256':hashlib.sha256(json.dumps(gained).encode()).hexdigest()}

def consequence_report(current:dict,candidate:dict,cases:list[dict],contracts:list[dict],target:str,affected_consumers:list[str],current_contract:dict,candidate_contract:dict):
    downstream_ids=[c['id'] for c in cases if c['target'] in set(affected_consumers)]
    before={i for i in downstream_ids if current.get(i)}; after={i for i in downstream_ids if candidate.get(i)}
    lost_task=sorted(before-after)
    contract_ids=[c['id'] for c in contracts if c.get('producer')==target or c['target'] in set(affected_consumers)]
    cb={i for i in contract_ids if current_contract.get(i)}; ca={i for i in contract_ids if candidate_contract.get(i)}
    lost_contract=sorted(cb-ca)
    return {'acceptable':not lost_task and not lost_contract,'affected_consumers':list(affected_consumers),'lost_downstream_task':len(lost_task),'lost_contract':len(lost_contract),'lost_task_sha256':hashlib.sha256(json.dumps(lost_task).encode()).hexdigest(),'lost_contract_sha256':hashlib.sha256(json.dumps(lost_contract).encode()).hexdigest()}

def meta_strategy_quality(strategy:dict,seed:str):
    jitter=(int(hashlib.sha256(seed.encode()).hexdigest()[:8],16)%1000)/1_000_000
    return float(strategy.get('robust',0.0)) - 0.25*float(strategy.get('shortcut',0.0)) + jitter
