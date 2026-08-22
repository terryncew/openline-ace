from __future__ import annotations
import hashlib, json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class LeakageTests(unittest.TestCase):
    def test_unit_tests_do_not_load_heldout_material(self):
        text=(ROOT/'tests'/'test_engine.py').read_text().lower(); self.assertNotIn('heldout',text); self.assertNotIn('oracle.json',text)
    def test_engine_is_bound_to_freeze_manifest(self):
        freeze=json.loads((ROOT/'protocol'/'engine_freeze.json').read_text())
        for name,expected in freeze['engine_files'].items(): self.assertEqual(hashlib.sha256((ROOT/'continuity_replay'/name).read_bytes()).hexdigest(),expected)
    def test_heldout_is_external_only(self):
        corpus=json.loads((ROOT/'heldout'/'corpus.json').read_text()); repos={c['repository'] for c in corpus['cases']}; self.assertEqual(repos,{'microsoft/agent-governance-toolkit','vercel-labs/portless'}); self.assertFalse(any(r.startswith('terryncew/') for r in repos))
    def test_tracked_blob_changes_match_event_paths(self):
        corpus=json.loads((ROOT/'heldout'/'corpus.json').read_text())
        for case in corpus['cases']:
            changed=set(case['observed_changed_paths'])
            for path,state in case['tracked_blob_states'].items(): self.assertEqual(state['base_blob']!=state['head_blob'],path in changed)
if __name__=='__main__': unittest.main()
