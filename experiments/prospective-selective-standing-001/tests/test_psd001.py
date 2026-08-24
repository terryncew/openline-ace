from pathlib import Path
import json, unittest
from psd001.core import (
    parse_metadata, build_t0_model, intervention_seed, select_interventions,
    oracle_ground_truth, openline_predict, artifact_join_predict,
    closure_index_predict, run_trial, confusion, missing_edge_safety,
    equivalence_mismatches, data_sufficiency, adjudicate, digest_obj
)
from psd001.oracle import decision_truth

ROOT=Path(__file__).resolve().parents[1]
TARGETS=["uv-auth","uv-git","uv-publish","uv-python","uv-resolver","uv-virtualenv"]

class PSD001Tests(unittest.TestCase):
    def setUp(self):
        self.metadata=json.loads((ROOT/"fixtures/metadata.json").read_text())
        self.proj=parse_metadata(self.metadata,TARGETS)
        self.t0=build_t0_model(self.proj,TARGETS,True,{t:"a"*64 for t in TARGETS})
        self.p=json.loads((ROOT/"preregistration.json").read_text())

    def test_target_projection_exact(self):
        self.assertEqual(set(self.proj["closures"]),set(TARGETS))

    def test_external_only_components(self):
        allc=set(self.proj["all_external_components"])
        self.assertTrue(any("serde@1.0.0" in c for c in allc))
        self.assertFalse(any("uv-auth@" in c for c in allc))

    def test_first_edge_kind_classification(self):
        a=self.proj["closures"]["uv-auth"]
        self.assertTrue(any("cc@1.0.0" in c for c in a["build"]))
        self.assertTrue(any("insta@1.0.0" in c for c in a["dev"]))
        self.assertFalse(any("cc@1.0.0" in c for c in a["runtime"]))

    def test_t0_has_exactly_30_decisions(self):
        self.assertEqual(len(self.t0["decisions"]),30)

    def test_all_t0_decisions_accepted(self):
        self.assertTrue(all(d["standing"]=="ACCEPTED" for d in self.t0["decisions"]))

    def test_receipts_are_hash_bound(self):
        for r in self.t0["receipts"]:
            marker=r["receipt_sha256"]
            body={k:v for k,v in r.items() if k!="receipt_sha256"}
            self.assertEqual(marker,digest_obj(body))

    def test_shared_component_truth_is_selective(self):
        shared=next(c for c in self.proj["union"]["uv-auth"] if "serde@1.0.0" in c)
        truth=oracle_ground_truth(self.t0,shared)
        affected=sum(truth.values())
        self.assertGreater(affected,0)
        self.assertLess(affected,30)

    def test_independent_oracle_matches_semantics(self):
        c=next(c for c in self.proj["union"]["uv-auth"] if "serde@1.0.0" in c)
        self.assertEqual(oracle_ground_truth(self.t0,c),decision_truth(self.t0,c))

    def test_artifact_join_overreopens_orthogonal_build_decision(self):
        c=next(c for c in self.proj["union"]["uv-auth"] if "ring@1.0.0" in c)
        art=artifact_join_predict(self.t0,c)
        self.assertEqual(art["decision:uv-auth:build_acceptance"],"REOPEN")
        truth=oracle_ground_truth(self.t0,c)
        self.assertFalse(truth["decision:uv-auth:build_acceptance"])

    def test_complete_graph_matches_decision_index(self):
        c=next(c for c in self.proj["union"]["uv-auth"] if "ring@1.0.0" in c)
        trial={"trial_id":"x","arm":"complete_graph","stratum":"single","component_id":c,"graph_damage":None}
        self.assertEqual(openline_predict(self.t0,trial),closure_index_predict(self.t0,c))

    def test_missing_edge_returns_undetermined_not_retain(self):
        c=next(c for c in self.proj["closures"]["uv-auth"]["runtime"] if "ring@1.0.0" in c)
        trial={"trial_id":"m","arm":"known_missing_edge","stratum":"single","component_id":c,
               "graph_damage":{"target":"uv-auth","kind":"runtime","known_incomplete":True}}
        pred=openline_predict(self.t0,trial)
        self.assertEqual(pred["decision:uv-auth:runtime_security_acceptance"],"UNDETERMINED")
        self.assertEqual(pred["decision:uv-auth:promotion_permission"],"UNDETERMINED")

    def test_absent_component_reopens_nothing(self):
        c=self.proj["absent_components"][0]
        trial={"trial_id":"a","arm":"complete_graph","stratum":"absent","component_id":c,"graph_damage":None}
        pred=openline_predict(self.t0,trial)
        self.assertTrue(all(v=="RETAIN" for v in pred.values()))

    def test_intervention_seed_deterministic(self):
        self.assertEqual(intervention_seed("x","y","z"),intervention_seed("x","y","z"))

    def test_selector_fails_closed_on_insufficient_pool(self):
        with self.assertRaises(Exception):
            select_interventions(self.proj,TARGETS,0,{"shared":100,"single":1,"absent":1,"missing_edge":1})

    def test_confusion_rewards_selective_graph(self):
        c=next(c for c in self.proj["closures"]["uv-auth"]["runtime"] if "ring@1.0.0" in c)
        tr=run_trial(self.t0,{"trial_id":"x","arm":"complete_graph","stratum":"single","component_id":c,"graph_damage":None})
        o=confusion([tr],"openline_evidence_graph")
        a=confusion([tr],"artifact_component_join")
        self.assertEqual(o["decision_recall"],1.0)
        self.assertGreater(o["decision_precision"],a["decision_precision"])

    def test_missing_edge_safety_counts_retain_as_failure(self):
        c=next(c for c in self.proj["closures"]["uv-auth"]["runtime"] if "ring@1.0.0" in c)
        tr=run_trial(self.t0,{"trial_id":"m","arm":"known_missing_edge","stratum":"single","component_id":c,
                              "graph_damage":{"target":"uv-auth","kind":"runtime","known_incomplete":True}})
        s=missing_edge_safety([tr])
        self.assertEqual(s["silent_false_retain_rate"],0.0)
        self.assertGreater(s["undetermined_count"],0)

    def test_equivalence_mismatch_zero_complete(self):
        c=next(c for c in self.proj["closures"]["uv-auth"]["runtime"] if "ring@1.0.0" in c)
        tr=run_trial(self.t0,{"trial_id":"x","arm":"complete_graph","stratum":"single","component_id":c,"graph_damage":None})
        self.assertEqual(equivalence_mismatches([tr]),0)

    def test_promotion_ignores_dev_only_revocation(self):
        c=next(c for c in self.proj["closures"]["uv-auth"]["dev"] if "insta@1.0.0" in c)
        truth=oracle_ground_truth(self.t0,c)
        self.assertTrue(truth["decision:uv-auth:test_security_acceptance"])
        self.assertFalse(truth["decision:uv-auth:promotion_permission"])

    def test_build_decision_never_falsified_by_security_signal(self):
        for c in self.proj["all_external_components"]:
            truth=oracle_ground_truth(self.t0,c)
            for t in TARGETS:
                self.assertFalse(truth[f"decision:{t}:build_acceptance"])

    def test_model_hash_stable(self):
        a=build_t0_model(self.proj,TARGETS,True,{t:"a"*64 for t in TARGETS})
        b=build_t0_model(self.proj,TARGETS,True,{t:"a"*64 for t in TARGETS})
        self.assertEqual(a["model_sha256"],b["model_sha256"])

if __name__=="__main__":
    unittest.main()
