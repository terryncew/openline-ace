from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from rcdl.cli import main
from rcdl.evaluator import evaluate
from rcdl.miner import filter_candidates
from rcdl.nuisance import nuisance_variants
from rcdl.raft import raft_candidate_clauses, run_intervention, run_scenario
from rcdl.reducer import inclusion_minimal_families

ROOT = Path(__file__).resolve().parents[1]


class ReducerTests(unittest.TestCase):
    def test_multiple_incomparable_minimal_families(self) -> None:
        families = inclusion_minimal_families(
            ["a", "b", "c"],
            lambda family: ({"a", "b"} <= family) or ("c" in family),
        )
        self.assertEqual(set(families), {frozenset({"a", "b"}), frozenset({"c"})})

    def test_empty_family_can_be_minimal(self) -> None:
        self.assertEqual(
            inclusion_minimal_families(["a", "b"], lambda family: True),
            (frozenset(),),
        )

    def test_search_bound_is_enforced(self) -> None:
        with self.assertRaises(ValueError):
            inclusion_minimal_families([str(index) for index in range(17)], lambda family: False)


class NuisanceTests(unittest.TestCase):
    def test_nuisance_transforms_preserve_pass(self) -> None:
        trace = run_scenario("healthy", 2)
        for clause in raft_candidate_clauses():
            baseline = evaluate(clause, trace)
            for variant in nuisance_variants(trace):
                with self.subTest(clause=clause.id, variant=variant.run_id):
                    observed = evaluate(clause, variant)
                    self.assertEqual(
                        (observed.passed, observed.trigger_count, observed.support_count),
                        (baseline.passed, baseline.trigger_count, baseline.support_count),
                    )

    def test_nuisance_transforms_preserve_detected_failure(self) -> None:
        clause = raft_candidate_clauses()[0]
        trace = run_intervention(clause.hook, "active", 2)
        self.assertFalse(evaluate(clause, trace).passed)
        self.assertTrue(all(not evaluate(clause, item).passed for item in nuisance_variants(trace)))


class MinerTests(unittest.TestCase):
    def test_empty_trace_set_cannot_propose_candidates(self) -> None:
        with self.assertRaises(ValueError):
            filter_candidates(raft_candidate_clauses(), ())


class CliTests(unittest.TestCase):
    def test_validate_clause(self) -> None:
        path = ROOT / "clauses" / "vote_once_per_term.json"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["validate-clause", str(path)])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output.getvalue())["valid"])

    def test_calibrate_and_verify(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["calibrate", "--output", directory, "--trials", "2"])
            self.assertEqual(code, 0)
            manifest = Path(directory) / "contract-manifest.json"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["verify-manifest", str(manifest)])
            self.assertEqual(code, 0)
            self.assertTrue(json.loads(output.getvalue())["verified"])

    def test_invalid_clause_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{}", encoding="utf-8")
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                code = main(["validate-clause", str(path)])
            self.assertEqual(code, 2)
            self.assertFalse(json.loads(error.getvalue())["ok"])

    def test_verify_pinned_reference(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["verify-reference"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output.getvalue())["verified"])

    def test_mine_candidates_proposes_without_granting_standing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            trace_path = Path(directory) / "successful.json"
            run_scenario("healthy", 3).write(trace_path)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(
                    [
                        "mine-candidates",
                        "--clauses",
                        str(ROOT / "clauses"),
                        "--traces",
                        str(trace_path),
                        "--min-support",
                        "1",
                    ]
                )
            result = json.loads(output.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(result["candidate_count"], 7)
            self.assertEqual(result["accepted_count"], 7)
            self.assertFalse(result["oracle_labels_used"])
            self.assertTrue(all("standing" not in item for item in result["results"]))


if __name__ == "__main__":
    unittest.main()
