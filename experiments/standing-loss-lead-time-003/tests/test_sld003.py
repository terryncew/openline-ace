import json
import unittest
from sld003.core import parse_state, summarize_structure, evaluate

class ParserTests(unittest.TestCase):
    def test_go_direct_and_indirect(self):
        text = """module x
require (
 github.com/a/a v1.2.3
 github.com/b/b v2.0.0 // indirect
)
"""
        rows = parse_state("go_mod", text)
        self.assertEqual({(r["name"],r["depth"]) for r in rows},
                         {("github.com/a/a",1),("github.com/b/b",2)})

    def test_cargo_transitive_depth(self):
        text = """
version = 4
[[package]]
name="root"
version="0.1.0"
dependencies=["a"]
[[package]]
name="a"
version="1.0.0"
source="registry+https://github.com/rust-lang/crates.io-index"
dependencies=["b"]
[[package]]
name="b"
version="2.0.0"
source="registry+https://github.com/rust-lang/crates.io-index"
"""
        rows = parse_state("cargo_lock", text)
        depths = {r["name"]:r["depth"] for r in rows}
        self.assertEqual(depths["a"],1)
        self.assertEqual(depths["b"],2)

    def test_uv_transitive_depth(self):
        text = """
version=1
[manifest]
members=["root"]
[[package]]
name="root"
version="0.1"
dependencies=[{name="a"}]
[[package]]
name="a"
version="1.0"
source={registry="https://pypi.org/simple"}
dependencies=[{name="b"}]
[[package]]
name="b"
version="2.0"
source={registry="https://pypi.org/simple"}
"""
        rows = parse_state("uv_lock_v1", text)
        depths = {r["name"]:r["depth"] for r in rows}
        self.assertEqual(depths["a"],1)
        self.assertEqual(depths["b"],2)

    def test_npm_transitive_depth(self):
        data = {"lockfileVersion":3,"packages":{
            "":{"dependencies":{"a":"1"}},
            "node_modules/a":{"name":"a","version":"1.0.0","dependencies":{"b":"1"}},
            "node_modules/b":{"name":"b","version":"2.0.0"}
        }}
        rows = parse_state("npm_lock_v3", json.dumps(data))
        depths = {r["name"]:r["depth"] for r in rows}
        self.assertEqual(depths["a"],1)
        self.assertEqual(depths["b"],2)

    def test_structure(self):
        s = summarize_structure([
            {"depth":1},{"depth":2},{"depth":3}
        ])
        self.assertEqual(s["transitive_nodes"],2)
        self.assertEqual(s["max_depth"],3)

class EvaluateTests(unittest.TestCase):
    def setUp(self):
        self.p = {
            "minimum_structural_ecosystems":4,
            "minimum_transitive_nodes_per_source":15,
            "minimum_true_events":10,
            "minimum_transitive_true_events":6,
            "minimum_event_ecosystems":3,
            "minimum_negative_controls":4,
            "minimum_negative_control_ecosystems":2,
            "minimum_incremental_coverage_over_direct":0.25,
            "maximum_false_invalidation_rate":0.05,
            "minimum_snapshot_watchlist_false_rate":0.5,
            "minimum_remediated_transitive_events":4,
            "minimum_remediation_observation_fraction":0.4,
            "minimum_positive_lead_fraction":0.75,
            "minimum_median_lead_hours":24.0,
        }
        self.structures = [
            {"ecosystem":e,"transitive_nodes":20,"nodes":30,"direct_nodes":10,"max_depth":3}
            for e in ["npm","PyPI","crates.io","Go"]
        ]

    def event(self, i, eco, cls="TRUE_AFFECTED", depth=2, rem=True):
        return {
            "event_id":str(i),"ecosystem":eco,"classification":cls,
            "depth":depth if cls=="TRUE_AFFECTED" else None,
            "published_at":"2025-01-01T00:00:00Z",
            "remediation_at":"2025-01-05T00:00:00Z" if rem and cls=="TRUE_AFFECTED" and depth>=2 else None,
        }

    def winning_events(self):
        ev=[]
        ecos=["npm","PyPI","crates.io","Go"]
        for i in range(8):
            ev.append(self.event(i, ecos[i%4], depth=2, rem=i<6))
        for i in range(4):
            ev.append(self.event(20+i, ecos[i%4], depth=1, rem=False))
        for i in range(4):
            ev.append(self.event(40+i, ecos[i%2], cls="STALE_WATCHLIST_CONTROL", rem=False))
        return ev

    def test_advantage_requires_depth_and_precision(self):
        r=evaluate(self.winning_events(), self.structures, self.p)
        self.assertEqual(r["verdict"],"EXTERNAL_TRANSITIVE_STANDING_ADVANTAGE")
        self.assertGreaterEqual(r["coverage"]["incremental_over_direct"],0.25)
        self.assertEqual(r["precision"]["olp_false_invalidation_rate"],0.0)
        self.assertEqual(r["precision"]["stale_snapshot_false_invalidation_rate"],1.0)

    def test_not_just_advisory_before_patch(self):
        ev=self.winning_events()
        for e in ev:
            if e["classification"]=="TRUE_AFFECTED":
                e["depth"]=1
        r=evaluate(ev,self.structures,self.p)
        self.assertEqual(r["verdict"],"DATA_INSUFFICIENT")

    def test_insufficient_ecosystem_diversity(self):
        ev=self.winning_events()
        for e in ev:
            e["ecosystem"]="npm"
        r=evaluate(ev,self.structures,self.p)
        self.assertEqual(r["verdict"],"DATA_INSUFFICIENT")

    def test_no_advantage_when_lead_too_short(self):
        ev=self.winning_events()
        for e in ev:
            if e.get("remediation_at"):
                e["remediation_at"]="2025-01-01T06:00:00Z"
        r=evaluate(ev,self.structures,self.p)
        self.assertEqual(r["verdict"],"NO_EXTERNAL_TRANSITIVE_STANDING_ADVANTAGE")

    def test_source_failure(self):
        r=evaluate([],[],self.p,source_ok=False)
        self.assertEqual(r["verdict"],"SOURCE_ACCESS_FAILED")

if __name__=="__main__":
    unittest.main()
