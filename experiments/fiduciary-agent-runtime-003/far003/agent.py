from __future__ import annotations
import json, random, pathlib
from .target import PATCHES, TARGETS, splice_target
from .evaluators import public_score
class ReferenceCodingAgent:
    def __init__(self,actor_id='coding-agent'): self.actor_id=actor_id
    def strategy(self,repo): return json.loads((repo/'agent/search/strategy.json').read_text())
    def propose_patch(self,repo:pathlib.Path,generation:int,seed:str):
        rng=random.Random(f'{seed}:{generation}'); strategy=self.strategy(repo); target=TARGETS[generation%len(TARGETS)]; ranked=[]
        old=(repo/'src/targetlib/core.py').read_text()
        for style,template in PATCHES[target].items():
            source=splice_target(old,template,target); (repo/'src/targetlib/core.py').write_text(source); ps=public_score(repo); ranked.append((ps,strategy.get(style,0.0)+rng.random()*1e-6,style,source))
        (repo/'src/targetlib/core.py').write_text(old); ranked.sort(reverse=True)
        _,_,style,source=ranked[0]; return target,style,source
    def propose_strategy(self,repo:pathlib.Path,generation:int):
        s=self.strategy(repo); step=0.12; target='shortcut' if generation%2==0 else 'robust'; s[target]=min(0.95,s[target]+step); other='robust' if target=='shortcut' else 'shortcut'; s[other]=1-s[target]; return s
