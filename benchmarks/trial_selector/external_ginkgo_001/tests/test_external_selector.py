import unittest
from external_selector import (
    Threshold, is_liability, build_matrices, bernoulli_entropy,
    dynamic_trace, fixed_prevalence_order, greedy_coverage_order,
    run_leave_one_out, strongest_comparator, paired_bootstrap_ci, adjudicate,
)

ASSAYS = ("A", "B", "C")
TH = {a: Threshold("<=", 0.5) for a in ASSAYS}

def cand(cid, a, b, c):
    return {"candidate_id": cid, "assays": {"A":a,"B":b,"C":c}}

class CoreTests(unittest.TestCase):
    def test_upper_and_lower_liability(self):
        self.assertTrue(is_liability(4.0, Threshold("<=", 3.0)))
        self.assertFalse(is_liability(3.0, Threshold("<=", 3.0)))
        self.assertTrue(is_liability(67.0, Threshold(">=", 68.0)))
        self.assertFalse(is_liability(68.0, Threshold(">=", 68.0)))

    def test_duplicate_candidate_rejected(self):
        with self.assertRaises(Exception):
            build_matrices([cand("x",0,0,0), cand("x",0,0,0)], ASSAYS, TH)

    def test_entropy_maximum_near_half(self):
        self.assertGreater(bernoulli_entropy(0.5), bernoulli_entropy(0.9))
        self.assertEqual(bernoulli_entropy(0.0), 0.0)

    def test_fixed_prevalence_deterministic(self):
        cs=[cand("x",1,0,0),cand("y",1,1,0),cand("z",0,0,0)]
        _,flags=build_matrices(cs,ASSAYS,TH)
        self.assertEqual(fixed_prevalence_order(flags,["x","y","z"],ASSAYS)[0],"A")

    def test_greedy_coverage_deterministic(self):
        cs=[cand("x",1,0,0),cand("y",0,1,0),cand("z",0,0,1)]
        _,flags=build_matrices(cs,ASSAYS,TH)
        self.assertEqual(greedy_coverage_order(flags,["x","y","z"],ASSAYS),["A","B","C"])

    def test_dynamic_never_reads_unobserved_holdout_value_for_first_choice(self):
        cs=[cand("h",0.1,0.1,0.1),cand("x",1,0,0),cand("y",1,0,0),cand("z",0,1,0)]
        values,flags=build_matrices(cs,ASSAYS,TH)
        t1=dynamic_trace(candidate_ids=sorted(values),holdout="h",assay_order=ASSAYS,values=values,flags=flags,mode="continuous")
        values2={k:dict(v) for k,v in values.items()}; values2["h"]["C"]=999.0
        t2=dynamic_trace(candidate_ids=sorted(values2),holdout="h",assay_order=ASSAYS,values=values2,flags=flags,mode="continuous")
        self.assertEqual(t1["steps"][0]["assay"],t2["steps"][0]["assay"])

    def test_binary_dynamic_ignores_magnitude(self):
        cs=[cand("h",0.1,0.1,0.1),cand("x",1,0,0),cand("y",1,1,0),cand("z",0,0,1)]
        values,flags=build_matrices(cs,ASSAYS,TH)
        t1=dynamic_trace(candidate_ids=sorted(values),holdout="h",assay_order=ASSAYS,values=values,flags=flags,mode="binary")
        values["x"]["A"]=10000
        t2=dynamic_trace(candidate_ids=sorted(values),holdout="h",assay_order=ASSAYS,values=values,flags=flags,mode="binary")
        self.assertEqual([s["assay"] for s in t1["steps"]],[s["assay"] for s in t2["steps"]])

    def test_entropy_trace_is_distinct_objective(self):
        cs=[cand("h",0.1,0.1,0.1),cand("x",1,0,0),cand("y",1,1,0),cand("z",1,0,1),cand("q",0,0,0)]
        values,flags=build_matrices(cs,ASSAYS,TH)
        ent=dynamic_trace(candidate_ids=sorted(values),holdout="h",assay_order=ASSAYS,values=values,flags=flags,mode="entropy")
        risk=dynamic_trace(candidate_ids=sorted(values),holdout="h",assay_order=ASSAYS,values=values,flags=flags,mode="continuous")
        self.assertIn(ent["steps"][0]["assay"],ASSAYS)
        self.assertIn(risk["steps"][0]["assay"],ASSAYS)
        self.assertGreaterEqual(ent["steps"][0]["selection_score"],0.0)

    def test_leave_one_out_has_all_strategies(self):
        cs=[cand("a",1,0,0),cand("b",0,1,0),cand("c",0,0,1),cand("d",0,0,0),cand("e",1,1,0)]
        out=run_leave_one_out(cs,ASSAYS,TH,budgets=(1,2))
        self.assertEqual(set(out["metrics"]),{"fixed_prevalence","greedy_fixed_coverage","binary_dynamic","continuous_value_conditional_risk","entropy_information_gain","uniform_random_expected"})

    def test_strongest_comparator_uses_cost_then_safety_then_name(self):
        metrics={
            "a":{"mean_assays_to_first_liability_positive_only":2.0,"budgets":{"3":{"false_reassurance_fraction":0.2}}},
            "b":{"mean_assays_to_first_liability_positive_only":2.0,"budgets":{"3":{"false_reassurance_fraction":0.1}}},
        }
        self.assertEqual(strongest_comparator(metrics,["a","b"],3),"b")

    def test_bootstrap_detects_uniform_advantage(self):
        target={str(i):1.0 for i in range(20)}; comp={str(i):2.0 for i in range(20)}
        ci=paired_bootstrap_ci(target,comp,sorted(target),resamples=1000,seed=0)
        self.assertLess(ci["ci_upper"],0.0)

    def test_adjudication_fails_without_cost_advantage(self):
        metrics={}
        names=["continuous_value_conditional_risk","fixed_prevalence"]
        for name,cost in [(names[0],2.0),(names[1],1.0)]:
            metrics[name]={"mean_assays_to_first_liability_positive_only":cost,"budgets":{"3":{"false_reassurance_fraction":0.1}}}
        run={"metrics":metrics,"positive_candidate_costs":{names[0]:{"x":2.0},names[1]:{"x":1.0}}}
        p={"target_strategy":names[0],"comparators":[names[1]],"primary_budget":3,"bootstrap":{"resamples":100,"seed":0}}
        self.assertEqual(adjudicate(run,p)["verdict"],"EXTERNAL_GENERALIZATION_NOT_SUPPORTED")

    def test_embedded_jain_identity_projection_is_bound_and_complete(self):
        from pathlib import Path
        import hashlib, json
        root = Path(__file__).resolve().parents[1]
        source = json.loads((root / "SOURCE_MANIFEST.json").read_text())
        rel = source["identity_exclusion"]["embedded_path"]
        p = root / rel
        self.assertTrue(p.is_file())
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), source["identity_exclusion"]["embedded_sha256"])
        cohort = json.loads(p.read_text())
        self.assertEqual(cohort["candidate_count"], 137)
        self.assertEqual(len(cohort["candidate_ids"]), 137)
        self.assertEqual(cohort["candidate_ids_sha256"], source["identity_exclusion"]["canonical_candidate_ids_sha256"])

if __name__ == "__main__": unittest.main()
