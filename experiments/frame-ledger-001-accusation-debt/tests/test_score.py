import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("score", ROOT / "src" / "score.py")
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)

ARMS = sorted(score.REQUIRED_ARMS)


def row(receiver, case, arm, risk, standing, action="no_action", basis=None, replicate=1):
    return {
        "case_id": case,
        "receiver": receiver,
        "arm": arm,
        "replicate": replicate,
        "wrongdoing_probability": risk,
        "standing": standing,
        "recommended_action": action,
        "basis_ids": basis or ["E1", "E2", "E3"],
        "_lineno": 1,
    }


def complete_case(receiver="m1", case="c1", replicate=1):
    vals = {
        "control": (5, 95, "no_action", ["E1"]),
        "matched_nuisance": (6, 94, "no_action", ["E1"]),
        "accusation_refuted": (15, 85, "monitor", ["E1", "A"]),
        "accusation_refuted_evidence_first": (10, 90, "no_action", ["E1"]),
        "explicit_revocation": (12, 88, "monitor", ["E1", "A"]),
        "calm_defense": (15, 85, "monitor", ["E1"]),
        "angry_defense": (25, 75, "formal_review", ["E1", "D"]),
    }
    return [row(receiver, case, arm, *vals[arm], replicate=replicate) for arm in ARMS]


class ScoreTests(unittest.TestCase):
    def test_primary_effects(self):
        out = score.summarize(complete_case())["receivers"]["m1"]
        e = out["effects"]
        self.assertEqual(e["accusation_debt_risk"], 10)
        self.assertEqual(e["accusation_specific_risk_vs_nuisance"], 9)
        self.assertEqual(e["order_sensitivity_risk"], 5)
        self.assertEqual(e["revocation_leakage_risk"], 7)
        self.assertEqual(e["revocation_leakage_standing"], 7)
        self.assertEqual(e["defense_penalty_risk"], 10)
        self.assertEqual(e["defense_action_escalation"], 1)
        self.assertEqual(out["evidence_contamination_rate"]["explicit_revocation"], 1)

    def test_replication_is_averaged_before_case_delta(self):
        rows = complete_case(replicate=1) + complete_case(replicate=2)
        for r in rows:
            if r["replicate"] == 2:
                r["wrongdoing_probability"] += 2
                r["standing"] -= 2
        e = score.summarize(rows)["receivers"]["m1"]["effects"]
        self.assertEqual(e["accusation_debt_risk"], 10)
        self.assertEqual(e["defense_penalty_risk"], 10)

    def test_missing_arm_fails_closed(self):
        rows = [r for r in complete_case() if r["arm"] != "angry_defense"]
        with self.assertRaisesRegex(ValueError, "missing arms"):
            score.summarize(rows)

    def test_unequal_replicates_fail_closed(self):
        rows = complete_case(replicate=1) + [row("m1", "c1", "control", 5, 95, replicate=2)]
        with self.assertRaisesRegex(ValueError, "replicate mismatch"):
            score.summarize(rows)

    def test_duplicate_replicate_fails_closed(self):
        rows = complete_case()
        rows.append(dict(rows[0]))
        with self.assertRaisesRegex(ValueError, "duplicate result key"):
            score.summarize(rows)

    def test_empty_results_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "no results"):
            score.summarize([])

    def test_receiver_divergence_is_reported_without_collapsing_to_score(self):
        rows = complete_case("m1") + complete_case("m2")
        for r in rows:
            if r["receiver"] == "m2" and r["arm"] == "explicit_revocation":
                r["wrongdoing_probability"] += 20
                r["standing"] -= 20
        out = score.summarize(rows)
        self.assertEqual(out["cross_receiver"]["revocation_leakage_risk"]["range"], 20)

    def test_bool_is_not_accepted_as_numeric_score(self):
        rows = complete_case()
        rows[0]["wrongdoing_probability"] = True
        with self.assertRaisesRegex(ValueError, "wrongdoing_probability"):
            score.summarize(rows)


if __name__ == "__main__":
    unittest.main()
