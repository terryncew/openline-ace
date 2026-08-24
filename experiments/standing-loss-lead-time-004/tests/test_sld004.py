import json
from pathlib import Path
import unittest
from sld004.core import (
    validate_case, predictions, confusion, data_sufficiency,
    select_primary_flat, bootstrap_precision_difference, adjudicate,
)

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    return json.loads((ROOT/"fixtures"/name).read_text())

class SLD004Tests(unittest.TestCase):
    def setUp(self):
        self.cases=[load("semantic_sibling.json"),load("artifact_fairness.json"),load("version_semantic_controls.json")]
        self.p=json.loads((ROOT/"preregistration.json").read_text())

    def test_all_synthetic_cases_admissible(self):
        for c in self.cases:
            self.assertTrue(validate_case(c)["admissible"], validate_case(c))

    def test_openline_reopens_only_declared_path(self):
        p=predictions(self.cases[0])
        self.assertEqual(p["openline_evidence_dag"],{"A"})
        self.assertEqual(p["artifact_component_join"],{"A","B"})

    def test_strong_artifact_join_gets_exact_component_membership(self):
        p=predictions(self.cases[1])
        self.assertEqual(p["artifact_component_join"],{"C"})
        self.assertNotIn("D",p["artifact_component_join"])
        self.assertNotIn("E",p["artifact_component_join"])

    def test_repo_scope_is_diagnostic_broad_join(self):
        p=predictions(self.cases[1])
        self.assertEqual(p["repo_scope_flat_join"],{"C","D","E"})

    def test_post_fix_not_flagged_by_exact_component_join(self):
        p=predictions(self.cases[2])
        self.assertNotIn("G",p["artifact_component_join"])

    def test_non_invalidating_component_membership_is_hard_control(self):
        p=predictions(self.cases[2])
        self.assertIn("H",p["artifact_component_join"])
        self.assertNotIn("H",p["openline_evidence_dag"])

    def test_any_change_reopens_everything(self):
        for c in self.cases:
            self.assertEqual(predictions(c)["any_change"],{d["decision_id"] for d in c["decisions"]})

    def test_headline_waits_until_t3(self):
        for c in self.cases:
            self.assertEqual(predictions(c)["headline_only"],set())

    def test_future_edge_source_is_rejected(self):
        c=json.loads(json.dumps(self.cases[0]))
        c["evidence_edges"][0]["source"]["published_at"]="2025-01-01T00:00:00Z"
        v=validate_case(c)
        self.assertFalse(v["admissible"])
        self.assertTrue(any("future_leakage_edge_source" in e for e in v["errors"]))

    def test_cycle_is_rejected(self):
        c=json.loads(json.dumps(self.cases[0]))
        c["evidence_edges"].append({
          "from":"decision:A","to":"component:X@1",
          "source":c["evidence_edges"][0]["source"]
        })
        v=validate_case(c)
        self.assertFalse(v["admissible"])
        self.assertIn("evidence_graph_not_dag",v["errors"])

    def test_case_requires_affected_and_unaffected(self):
        c=json.loads(json.dumps(self.cases[0]))
        for d in c["decisions"]: d["ground_truth"]["affected"]=True
        self.assertIn("case_has_no_unaffected_decision",validate_case(c)["errors"])

    def test_fixture_openline_has_better_precision(self):
        a=confusion(self.cases,"openline_evidence_dag")
        b=confusion(self.cases,"artifact_component_join")
        self.assertEqual(a["decision_recall"],1.0)
        self.assertEqual(a["decision_precision"],1.0)
        self.assertEqual(b["decision_recall"],1.0)
        self.assertLess(b["decision_precision"],1.0)

    def test_primary_flat_prefers_more_precise_recall_equivalent(self):
        m={x:confusion(self.cases,x) for x in ("artifact_component_join","repo_scope_flat_join")}
        self.assertEqual(select_primary_flat(m),"artifact_component_join")

    def test_bootstrap_is_deterministic(self):
        a=bootstrap_precision_difference(self.cases,"artifact_component_join",resamples=500,seed=0)
        b=bootstrap_precision_difference(self.cases,"artifact_component_join",resamples=500,seed=0)
        self.assertEqual(a,b)

    def test_fixture_set_is_below_f1_case_minimum(self):
        s=data_sufficiency(self.cases,self.p)
        self.assertFalse(s["sufficient"])
        self.assertFalse(s["checks"]["minimum_cases"])

    def test_adjudication_refuses_small_fixture_set(self):
        self.assertEqual(adjudicate(self.cases,self.p)["verdict"],"DATA_INSUFFICIENT")

    def test_unknown_negative_category_rejected(self):
        c=json.loads(json.dumps(self.cases[0]))
        c["decisions"][1]["negative_control_category"]="made_up"
        self.assertFalse(validate_case(c)["admissible"])

    def test_missing_source_hash_rejected(self):
        c=json.loads(json.dumps(self.cases[0]))
        c["signal"]["source"]["captured_sha256"]=""
        self.assertFalse(validate_case(c)["admissible"])

    def test_t3_must_follow_signal(self):
        c=json.loads(json.dumps(self.cases[0]))
        c["decisions"][0]["ground_truth"]["t3"]="2024-02-01T00:00:00Z"
        self.assertFalse(validate_case(c)["admissible"])

if __name__=="__main__":
    unittest.main()
