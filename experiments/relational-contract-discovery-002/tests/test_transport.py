from __future__ import annotations

import unittest
from pathlib import Path

import rcdl
from rcdl.evaluator import evaluate
from rcdl.nuisance import nuisance_variants
from rcdl.otel import trace_from_otlp, trace_to_otlp

from rcdl002.workflow import run_intervention, workflow_candidate_clauses

ROOT = Path(__file__).resolve().parents[1]


def signature(result) -> tuple[bool, int, int, int]:
    return (
        result.passed,
        result.trigger_count,
        result.support_count,
        result.violation_count,
    )


class FrozenEngineTransportTests(unittest.TestCase):
    def test_rcdl_engine_is_imported_from_experiment_001(self) -> None:
        engine_path = Path(rcdl.__file__).resolve()
        self.assertIn("relational-contract-discovery-001", engine_path.parts)
        self.assertNotIn("relational-contract-discovery-002", engine_path.parts)
        self.assertFalse((ROOT / "rcdl").exists())

    def test_otel_round_trip_preserves_every_active_and_sham_result(self) -> None:
        for clause in workflow_candidate_clauses():
            for arm in ("active", "sham"):
                with self.subTest(clause=clause.id, arm=arm):
                    run = run_intervention(clause.hook, arm, 31)
                    observed = trace_from_otlp(trace_to_otlp(run.trace))
                    self.assertEqual(
                        signature(evaluate(clause, observed)),
                        signature(evaluate(clause, run.trace)),
                    )

    def test_nuisance_variants_preserve_every_active_and_sham_result(self) -> None:
        for clause in workflow_candidate_clauses():
            for arm in ("active", "sham"):
                run = run_intervention(clause.hook, arm, 37)
                baseline = signature(evaluate(clause, run.trace))
                for variant in nuisance_variants(run.trace):
                    with self.subTest(
                        clause=clause.id,
                        arm=arm,
                        variant=variant.run_id,
                    ):
                        self.assertEqual(signature(evaluate(clause, variant)), baseline)

    def test_candidate_grammar_remains_finite_and_actionable(self) -> None:
        clauses = workflow_candidate_clauses()
        self.assertEqual(len(clauses), 5)
        self.assertEqual(len({clause.id for clause in clauses}), 5)
        self.assertEqual(len({clause.hook for clause in clauses}), 5)
        self.assertTrue(
            all(clause.to_dict()["intervention"]["energy"] == 1 for clause in clauses)
        )


if __name__ == "__main__":
    unittest.main()
