from __future__ import annotations
import json, pathlib, random
from .evaluators import public_score
from .substrate import TARGET_ORDER, PATCHES, apply, source_for
class ReferenceDependencyAgent:
    def __init__(self,actor_id='coding-agent'):
        self.actor_id=actor_id; self.denied={k:set() for k in PATCHES}; self.committed=set()
    def strategy(self,repo): return json.loads((repo/'agent/search/strategy.json').read_text())
    def feedback(self,target,style,disposition):
        if disposition=='DENY': self.denied[target].add(style)
        if disposition=='COMMIT': self.committed.add(target)
    def propose_patch(self,repo:pathlib.Path,generation:int,seed:str):
        target=TARGET_ORDER[generation%len(TARGET_ORDER)]
        if target in self.committed:
            style='robust'; return target,style,source_for(repo,target)
        strategy=self.strategy(repo); old=source_for(repo,target); ranked=[]
        rng=random.Random(f'{seed}:{generation}:{target}')
        for style,source in PATCHES[target].items():
            if style in self.denied[target]: continue
            apply(repo,target,source); ps=public_score(repo,target)
            ranked.append((ps,strategy.get(style,0.0)+rng.random()*1e-9,style,source))
        apply(repo,target,old)
        if not ranked:
            style='robust'; return target,style,PATCHES[target]['robust']
        ranked.sort(reverse=True); _,_,style,source=ranked[0]; return target,style,source
    def propose_strategy(self,repo,generation):
        s=self.strategy(repo); step=0.10
        if (generation//4)%2==0:
            s['robust']=min(0.95,s.get('robust',0.4)+step); s['shortcut']=1-s['robust']
        else:
            s['shortcut']=min(0.95,s.get('shortcut',0.6)+step); s['robust']=1-s['shortcut']
        return s
