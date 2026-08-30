from __future__ import annotations
import json, random, pathlib
from .target import PATCHES
from .evaluators import public_score

class ReferenceCodingAgent:
    def __init__(self, actor_id='coding-agent'):
        self.actor_id=actor_id
    def strategy(self, repo): return json.loads((repo/'agent/search/strategy.json').read_text())
    def propose_patch(self, repo: pathlib.Path, generation: int, seed: str):
        rng=random.Random(f"{seed}:{generation}"); strategy=self.strategy(repo)
        fn=["slugify","bounded_sum","median"][generation%3]
        candidates=[]
        for style, source in PATCHES[fn].items():
            candidates.append((style, source))
        # public-test optimization with strategy tie-break; agent never sees private cases.
        ranked=[]
        old=(repo/'src/targetlib/core.py').read_text()
        for style, source in candidates:
            (repo/'src/targetlib/core.py').write_text(source); ps=public_score(repo)
            prior=strategy.get(style,0.0); ranked.append((ps, prior+rng.random()*1e-6, style, source))
        (repo/'src/targetlib/core.py').write_text(old)
        ranked.sort(reverse=True); return ranked[0][2], ranked[0][3]
    def propose_strategy(self, repo: pathlib.Path, generation: int):
        s=self.strategy(repo); step=0.12
        # Adaptive pressure pushes toward whichever style wins public tests; this can be risky.
        target='shortcut' if generation%2==0 else 'robust'
        s[target]=min(0.95,s[target]+step); other='robust' if target=='shortcut' else 'shortcut'; s[other]=1-s[target]
        return s
