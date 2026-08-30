from __future__ import annotations
import pathlib, tempfile, unittest
from far002.classifier import classify
from far002.gate import Gate
from far002.model import Proposal, Receipt
from far002.receipts import Registry
from far002.canonical import sha256

class T(unittest.TestCase):
 def setUp(self):
  self.reg=Registry({'principal':('PRINCIPAL_AUTHORITY','p'),'task':('TASK_EVALUATOR','t'),'consequence':('CONSEQUENCE_EVALUATOR','c'),'meta':('META_EVALUATOR','m'),'peer':('PEER_AGENT','x'),'agent':('AGENT','a')}); self.g=Gate(self.reg)
 def p(self,path,tier='TIER1_OPERATIONAL'): return Proposal('p','agent','PATCH',(path,),sha256(path),tier,False,'')
 def valid(self,p,meta=False):
  rows=[self.reg.issue(issuer_id='task',kind='TASK_EVALUATION',subject_id=p.proposal_id,subject_sha256=p.payload_sha256,claims={'passed':True}),self.reg.issue(issuer_id='consequence',kind='CONSEQUENCE',subject_id=p.proposal_id,subject_sha256=p.payload_sha256,claims={'acceptable':True}),self.reg.issue(issuer_id='principal',kind='MANDATE',subject_id=p.proposal_id,subject_sha256=p.payload_sha256,claims={'allowed_actions':['PATCH'],'allowed_path_prefixes':['src/','agent/search/']})]
  if meta: rows.append(self.reg.issue(issuer_id='meta',kind='META_EVALUATION',subject_id=p.proposal_id,subject_sha256=p.payload_sha256,claims={'passed':True}))
  return tuple(rows)
 def test_source_tier1(self): self.assertEqual(classify(self.p('src/x.py'))[0],'TIER1_OPERATIONAL')
 def test_search_launders_upward(self): self.assertEqual(classify(self.p('agent/search/s.json'))[0],'TIER2_GENERATOR')
 def test_tests_are_constitutional(self): self.assertEqual(classify(self.p('tests/test_x.py'))[0],'TIER3_CONSTITUTIONAL')
 def test_hidden_eval_constitutional(self): self.assertEqual(classify(self.p('.openline/evaluators/x.py'))[0],'TIER3_CONSTITUTIONAL')
 def test_valid_source_commits(self):
  p=self.p('src/x.py'); self.assertEqual(self.g.decide(p,self.valid(p)).disposition,'COMMIT')
 def test_tier2_requires_meta(self):
  p=self.p('agent/search/s.json'); self.assertEqual(self.g.decide(p,self.valid(p)).disposition,'QUARANTINE'); self.assertEqual(self.g.decide(p,self.valid(p,True)).disposition,'COMMIT')
 def test_constitutional_never_commits_even_with_receipts(self):
  p=self.p('tests/test_x.py'); self.assertEqual(self.g.decide(p,self.valid(p)).disposition,'DENY')
 def test_peer_go_is_not_mandate(self):
  p=self.p('src/x.py'); rows=list(self.valid(p)); rows=[r for r in rows if r.kind!='MANDATE']; rows.append(self.reg.issue(issuer_id='peer',kind='MANDATE',subject_id=p.proposal_id,subject_sha256=p.payload_sha256,claims={'allowed_actions':['PATCH'],'allowed_path_prefixes':['src/']})); self.assertEqual(self.g.decide(p,tuple(rows)).disposition,'DENY')
 def test_forged_principal_receipt_denied(self):
  p=self.p('src/x.py'); rows=list(self.valid(p)); rows=[r for r in rows if r.kind!='MANDATE']; rows.append(Receipt('fake','agent','PRINCIPAL_AUTHORITY','MANDATE',p.proposal_id,p.payload_sha256,{'allowed_actions':['PATCH'],'allowed_path_prefixes':['src/']},'bad')); self.assertEqual(self.g.decide(p,tuple(rows)).disposition,'DENY')
 def test_self_issued_task_evidence_denied(self):
  p=self.p('src/x.py'); rows=list(self.valid(p)); rows=[r for r in rows if r.kind!='TASK_EVALUATION']; rows.append(self.reg.issue(issuer_id='agent',kind='TASK_EVALUATION',subject_id=p.proposal_id,subject_sha256=p.payload_sha256,claims={'passed':True})); self.assertEqual(self.g.decide(p,tuple(rows)).disposition,'DENY')

if __name__=='__main__': unittest.main()
