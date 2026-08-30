from __future__ import annotations
import json, pathlib, tempfile, unittest
from far003.agent import ReferenceCodingAgent
from far003.canonical import sha256
from far003.classifier import classify
from far003.controls import run_controls
from far003.evaluators import admission_report, calibration_assertions, isolated_passes
from far003.gate import Gate
from far003.model import Proposal, Receipt
from far003.receipts import Registry
from far003.scope import assess_scope, changed_symbols, load_manifest
from far003.target import BASELINE, PATCHES, init_repo, splice_target
ROOT=pathlib.Path(__file__).resolve().parents[1]
class T(unittest.TestCase):
 def setUp(self): self.reg=Registry({'principal':('PRINCIPAL_AUTHORITY','p'),'task':('TASK_EVALUATOR','t'),'consequence':('CONSEQUENCE_EVALUATOR','c'),'meta':('META_EVALUATOR','m'),'peer':('PEER_AGENT','x'),'agent':('AGENT','a')}); self.g=Gate(self.reg)
 def p(self,path,tier='TIER1_OPERATIONAL'): return Proposal('p','agent','PATCH',(path,),sha256(path),tier,False,'')
 def valid(self,p,meta=False):
  rows=[self.reg.issue(issuer_id='task',kind='TASK_EVALUATION',subject_id=p.proposal_id,subject_sha256=p.payload_sha256,claims={'passed':True}),self.reg.issue(issuer_id='consequence',kind='CONSEQUENCE',subject_id=p.proposal_id,subject_sha256=p.payload_sha256,claims={'acceptable':True}),self.reg.issue(issuer_id='principal',kind='MANDATE',subject_id=p.proposal_id,subject_sha256=p.payload_sha256,claims={'allowed_actions':['PATCH'],'allowed_path_prefixes':['src/','agent/search/']})]
  if meta: rows.append(self.reg.issue(issuer_id='meta',kind='META_EVALUATION',subject_id=p.proposal_id,subject_sha256=p.payload_sha256,claims={'passed':True}))
  return tuple(rows)
 def test_source_tier1(self): self.assertEqual(classify(self.p('src/x.py'))[0],'TIER1_OPERATIONAL')
 def test_search_launders_upward(self): self.assertEqual(classify(self.p('agent/search/s.json'))[0],'TIER2_GENERATOR')
 def test_tests_constitutional(self): self.assertEqual(classify(self.p('tests/test_x.py'))[0],'TIER3_CONSTITUTIONAL')
 def test_scope_manifest_constitutional(self): self.assertEqual(classify(self.p('experiments/fiduciary-agent-runtime-003/SCOPE_MANIFEST.json'))[0],'TIER3_CONSTITUTIONAL')
 def test_tier2_requires_meta(self):
  p=self.p('agent/search/s.json'); self.assertEqual(self.g.decide(p,self.valid(p)).disposition,'QUARANTINE'); self.assertEqual(self.g.decide(p,self.valid(p,True)).disposition,'COMMIT')
 def test_constitutional_never_commits(self):
  p=self.p('tests/test_x.py'); self.assertEqual(self.g.decide(p,self.valid(p)).disposition,'DENY')
 def test_peer_go_not_mandate(self):
  p=self.p('src/x.py'); rows=[r for r in self.valid(p) if r.kind!='MANDATE']; rows.append(self.reg.issue(issuer_id='peer',kind='MANDATE',subject_id=p.proposal_id,subject_sha256=p.payload_sha256,claims={'allowed_actions':['PATCH'],'allowed_path_prefixes':['src/']})); self.assertEqual(self.g.decide(p,tuple(rows)).disposition,'DENY')
 def test_forged_principal_denied(self):
  p=self.p('src/x.py'); rows=[r for r in self.valid(p) if r.kind!='MANDATE']; rows.append(Receipt('fake','agent','PRINCIPAL_AUTHORITY','MANDATE',p.proposal_id,p.payload_sha256,{'allowed_actions':['PATCH'],'allowed_path_prefixes':['src/']},'bad')); self.assertEqual(self.g.decide(p,tuple(rows)).disposition,'DENY')
 def test_splice_changes_only_target(self):
  cand=splice_target(BASELINE,PATCHES['bounded_sum']['robust'],'bounded_sum'); self.assertEqual(changed_symbols(BASELINE,cand),{'bounded_sum'})
 def test_multi_symbol_diff_fails_scope(self):
  manifest=load_manifest(ROOT); cand=splice_target(BASELINE,PATCHES['bounded_sum']['robust'],'bounded_sum'); cand=splice_target(cand,PATCHES['slugify']['robust'],'slugify'); self.assertFalse(assess_scope(target='bounded_sum',before=BASELINE,candidate=cand,manifest=manifest)['scope_ok'])
 def test_module_level_change_fails_scope(self):
  manifest=load_manifest(ROOT); cand='FLAG=1\n'+splice_target(BASELINE,PATCHES['bounded_sum']['robust'],'bounded_sum'); self.assertFalse(assess_scope(target='bounded_sum',before=BASELINE,candidate=cand,manifest=manifest)['scope_ok'])
 def test_incremental_assertion_rule(self):
  cases=[{'id':'a','target':'bounded_sum'},{'id':'b','target':'median'}]; r=admission_report(current_pass={'b'},candidate_pass={'a','b'},cases=cases,target='bounded_sum'); self.assertTrue(r['passed'])
 def test_unaffected_regression_vetoes(self):
  cases=[{'id':'a','target':'bounded_sum'},{'id':'b','target':'median'}]; r=admission_report(current_pass={'b'},candidate_pass={'a'},cases=cases,target='bounded_sum'); self.assertFalse(r['passed']); self.assertEqual(r['unaffected_lost'],1)
 def test_power_controls_all_pass(self): self.assertTrue(run_controls(ROOT)['passed'])
if __name__=='__main__': unittest.main()
