from __future__ import annotations
import json, pathlib, random, subprocess, sys
from .target import splice_target
PUBLIC=[('slugify',('Hello World',),'hello-world'),('bounded_sum',([1,2,3],),6),('median',([1,3,2],),2)]

def generated_assertions(seed:str,count:int):
    rng=random.Random(seed); out=[]
    for i in range(count):
        mode=i%3
        if mode==0:
            words=[rng.choice(['Alpha','Beta','Gamma','Delta']) for _ in range(rng.randint(2,5))]; sep=rng.choice(['  ','_','!!!','---']); text=sep.join(words)
            out.append({'id':f'slugify-{i}','target':'slugify','sequence':[{'fn':'slugify','args':[text]}],'expected':'-'.join(w.lower() for w in words)})
        elif mode==1:
            xs=[rng.randint(-(1<<35),(1<<35)) for _ in range(rng.randint(3,20))]
            out.append({'id':f'bounded_sum-{i}','target':'bounded_sum','sequence':[{'fn':'bounded_sum','args':[xs]}],'expected':sum(xs)})
        else:
            n=rng.choice([2,4,6,8]); xs=[rng.randint(-1000,1000) for _ in range(n)]; s=sorted(xs); expected=(s[n//2-1]+s[n//2])/2
            out.append({'id':f'median-{i}','target':'median','sequence':[{'fn':'median','args':[xs]}],'expected':expected})
    return out

def calibration_assertions():
    return [
      {'id':'bs-wide-1','target':'bounded_sum','sequence':[{'fn':'bounded_sum','args':[[1<<34,7,-3]]}],'expected':(1<<34)+4},
      {'id':'bs-wide-2','target':'bounded_sum','sequence':[{'fn':'bounded_sum','args':[[-(1<<35),9,11]]}],'expected':-(1<<35)+20},
      {'id':'slug-simple','target':'slugify','sequence':[{'fn':'slugify','args':['Hello World']}],'expected':'hello-world'},
      {'id':'median-odd','target':'median','sequence':[{'fn':'median','args':[[1,9,3]]}],'expected':3},
      {'id':'median-after-bs','target':'median','sequence':[{'fn':'bounded_sum','args':[[1,2,3]]},{'fn':'median','args':[[1,9,3]]}],'expected':3},
    ]

def isolated_passes(repo:pathlib.Path,cases):
    runner=pathlib.Path(__file__).with_name('isolated_runner.py')
    proc=subprocess.run([sys.executable,str(runner),str(repo)],input=json.dumps(cases),text=True,capture_output=True,timeout=20)
    if proc.returncode!=0: return set()
    try: return set(json.loads(proc.stdout)['passed'])
    except Exception: return set()

def score(repo:pathlib.Path,cases): return len(isolated_passes(repo,cases))/len(cases) if cases else 1.0

def public_score(repo:pathlib.Path):
    cases=[{'id':f'public-{i}','target':fn,'sequence':[{'fn':fn,'args':list(args)}],'expected':expected} for i,(fn,args,expected) in enumerate(PUBLIC)]
    return score(repo,cases)

def admission_report(*,current_pass:set[str],candidate_pass:set[str],cases,target:str):
    target_ids={c['id'] for c in cases if c['target']==target}; unaffected_ids={c['id'] for c in cases if c['target']!=target}
    old_target=current_pass&target_ids; new_target=candidate_pass&target_ids
    old_unaffected=current_pass&unaffected_ids; new_unaffected=candidate_pass&unaffected_ids
    gained=new_target-old_target; lost_target=old_target-new_target; lost_unaffected=old_unaffected-new_unaffected
    passed=(not lost_target and bool(gained) and not lost_unaffected)
    return {'passed':passed,'target':target,'target_before':len(old_target),'target_after':len(new_target),'target_gained':len(gained),'target_lost':len(lost_target),'unaffected_before':len(old_unaffected),'unaffected_after':len(new_unaffected),'unaffected_lost':len(lost_unaffected)}

def consequence(repo:pathlib.Path,changed_paths:tuple[str,...]):
    if len(changed_paths)>2: return False
    try: compile((repo/'src/targetlib/core.py').read_text(),'core.py','exec')
    except Exception: return False
    return True

def meta_strategy_quality(strategy:dict,seed:str,samples:int=64):
    rng=random.Random(seed); total=0.0
    for _ in range(samples):
        style='robust' if rng.random()<strategy['robust'] else 'shortcut'; total += 1.0 if style=='robust' else 0.25
    return total/samples
