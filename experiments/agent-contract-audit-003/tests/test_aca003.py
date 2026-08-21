import json,tempfile,unittest
from pathlib import Path
from aca003.model import check_source_packet
from aca003.bundle import build_bundle
from aca003.receipt import verify_receipt
from aca003.projections import claim_graph_projection,receipt_gate_projection
ROOT=Path(__file__).resolve().parents[1]
KEY=bytes.fromhex("11"*32)

class T(unittest.TestCase):
    def p(self,n): return json.loads((ROOT/"fixtures"/n).read_text())
    def test_eligible(self): self.assertTrue(check_source_packet(self.p("eligible-supported.json")).eligible)
    def test_conformance_ineligible(self):
        e=check_source_packet(self.p("ineligible-conformance.json")); self.assertFalse(e.eligible); self.assertIn("external_run_not_completed",e.reasons)
    def test_ritual_ineligible(self):
        e=check_source_packet(self.p("ineligible-ritual.json")); self.assertFalse(e.eligible); self.assertIn("standing_not_supported",e.reasons)
    def test_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            build_bundle(self.p("eligible-supported.json"),Path(td),KEY)
            r=json.loads((Path(td)/"contract-standing.receipt.json").read_text()); d=json.loads((Path(td)/"contract-standing.disclosure.json").read_text())
            verify_receipt(r,d); self.assertEqual(r["policy_authority"],"NONE"); self.assertEqual(r["runtime_permission"],"NONE")
    def test_projections_no_authority(self):
        with tempfile.TemporaryDirectory() as td:
            build_bundle(self.p("eligible-supported.json"),Path(td),KEY)
            r=json.loads((Path(td)/"contract-standing.receipt.json").read_text()); d=json.loads((Path(td)/"contract-standing.disclosure.json").read_text())
            cg=claim_graph_projection(r,d); rg=receipt_gate_projection(r,d)
            self.assertEqual(cg["candidate_relation"]["admission_status"],"UNADMITTED"); self.assertTrue(cg["receiver_policy_required"])
            self.assertTrue(rg["evidence_only"]); self.assertIsNone(rg["requested_disposition"]); self.assertIsNone(rg["commit_authorization"])
    def test_tamper_disclosure(self):
        with tempfile.TemporaryDirectory() as td:
            build_bundle(self.p("eligible-supported.json"),Path(td),KEY)
            r=json.loads((Path(td)/"contract-standing.receipt.json").read_text()); d=json.loads((Path(td)/"contract-standing.disclosure.json").read_text()); d["contract_text"]+="x"
            with self.assertRaises(ValueError): verify_receipt(r,d)
    def test_tamper_authority(self):
        with tempfile.TemporaryDirectory() as td:
            build_bundle(self.p("eligible-supported.json"),Path(td),KEY)
            r=json.loads((Path(td)/"contract-standing.receipt.json").read_text()); d=json.loads((Path(td)/"contract-standing.disclosure.json").read_text()); r["policy_authority"]="COMMIT"
            with self.assertRaises(ValueError): verify_receipt(r,d)
    def test_independent_fail(self):
        p=self.p("eligible-supported.json"); p["independent_verification"]["status"]="FAIL"; self.assertFalse(check_source_packet(p).eligible)
if __name__=="__main__": unittest.main()
