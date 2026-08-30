from __future__ import annotations
import json,pathlib,tempfile,unittest,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from far005.claim_graph import ClaimGraph,StandingGate
from far005.controls import run_controls
from far005.evaluators import generated_cases,contract_cases,pass_map,target_admission,consequence_report
from far005.scope import load_manifest,assess_patch
from far005.substrate import init_repo,source_for,apply,PATCHES,NODE_PATHS
class FAR005Tests(unittest.TestCase):
 def test_manifest_dag(self):
  m=load_manifest(ROOT); self.assertEqual(m['nodes']['parse']['direct_dependencies'],['codec']); self.assertEqual(set(m['nodes']['pipeline']['direct_dependencies']),{'parse','transform'}); self.assertEqual(m['transitive_consumers']['codec'],['parse','pipeline'])
 def test_parse_blocked_before_codec(self):
  with tempfile.TemporaryDirectory() as td:
   r=pathlib.Path(td)/'r'; init_repo(r); c=generated_cases('x',6); before=pass_map(r,c); old=source_for(r,'parse'); apply(r,'parse',PATCHES['parse']['robust']); after=pass_map(r,c); apply(r,'parse',old); self.assertFalse(target_admission(before,after,c,'parse')['passed'])
 def test_transform_trap_local_pass_remote_fail(self):
  with tempfile.TemporaryDirectory() as td:
   r=pathlib.Path(td)/'r'; init_repo(r); c=generated_cases('x',6); cc=contract_cases('y',4); b=pass_map(r,c); bc=pass_map(r,cc); old=source_for(r,'transform'); cand=PATCHES['transform']['shortcut']; apply(r,'transform',cand); a=pass_map(r,c); ac=pass_map(r,cc); apply(r,'transform',old); m=load_manifest(ROOT); sr=assess_patch(manifest=m,node='transform',path=NODE_PATHS['transform'],before=old,candidate=cand); ar=target_admission(b,a,c,'transform'); cr=consequence_report(b,a,c,cc,'transform',sr['affected_consumers'],bc,ac); self.assertTrue(ar['passed']); self.assertFalse(cr['acceptable'])
 def test_new_import_edge_denied(self):
  m=load_manifest(ROOT); old=PATCHES['transform']['robust']; bad='from workers import shim\n'+old; sr=assess_patch(manifest=m,node='transform',path=NODE_PATHS['transform'],before=old,candidate=bad,extra_paths=('src/workers/shim.py',)); self.assertFalse(sr['scope_ok'])
 def test_selective_recall(self):
  g=ClaimGraph(); c=g.add('codec','c',(),('e',)); t=g.add('transform','t',(),('e',)); p=g.add('parse','p',(c.receipt_id,),('e',)); l=g.add('pipeline','l',(p.receipt_id,t.receipt_id),('e',)); g.revoke(c.receipt_id); self.assertEqual(g.node_standing(),{'codec':'REVOKED','transform':'ACTIVE','parse':'REOPEN','pipeline':'REOPEN'}); self.assertEqual(StandingGate(g).rely('pipeline'),'DENY'); self.assertEqual(StandingGate(g).rely('transform'),'COMMIT')
 def test_power_controls(self): self.assertTrue(run_controls(ROOT)['passed'])
 def test_prereg_halt_disabled(self): self.assertFalse(json.loads((ROOT/'PREREGISTRATION.json').read_text())['protocol']['halt_saturated_active'])
if __name__=='__main__': unittest.main()
