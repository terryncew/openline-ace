from __future__ import annotations
import json, unittest
from pathlib import Path
from continuity_replay.baselines import flat_latest_state, global_invalidation
from continuity_replay.engine import selective_reopen
from continuity_replay.metrics import score
from continuity_replay.model import ClaimGraph
ROOT=Path(__file__).resolve().parents[1]
class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((ROOT/'fixtures'/'development.json').read_text()); cls.graph=ClaimGraph.from_mapping(cls.fixture['graph']); cls.changed=frozenset(cls.fixture['observed_changed_paths']); cls.warranted=frozenset(cls.fixture['warranted'])
    def test_selective_reopening_propagates_descendants(self): self.assertEqual(selective_reopen(self.graph,self.changed).reopened,frozenset({'claim-a','claim-a-child'}))
    def test_selective_reopening_retains_unrelated_claim(self): self.assertEqual(selective_reopen(self.graph,self.changed).retained,frozenset({'claim-b'}))
    def test_global_invalidation_overreviews(self): self.assertEqual(score(global_invalidation(self.graph,self.changed),self.warranted)['excess_reviews'],1)
    def test_flat_latest_state_misses_descendant(self): self.assertEqual(score(flat_latest_state(self.graph,self.changed),self.warranted)['missed_reopenings'],1)
    def test_no_change_reopens_nothing(self): self.assertFalse(selective_reopen(self.graph,frozenset()).reopened)
    def test_cycle_is_bounded(self):
        graph=ClaimGraph.from_mapping({'claims':['a','b'],'edges':[['artifact/x','a'],['a','b'],['b','a']]}); self.assertEqual(selective_reopen(graph,frozenset({'artifact/x'})).reopened,frozenset({'a','b'}))
    def test_unknown_changed_artifact_has_no_effect(self): self.assertFalse(selective_reopen(self.graph,frozenset({'artifact/unknown'})).reopened)
    def test_metrics_are_exact(self):
        m=score(selective_reopen(self.graph,self.changed),self.warranted); self.assertEqual((m['precision'],m['recall'],m['f1']),(1.0,1.0,1.0))
if __name__=='__main__': unittest.main()
