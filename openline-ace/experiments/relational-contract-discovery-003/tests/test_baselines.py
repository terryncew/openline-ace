from __future__ import annotations

import unittest

from rcdl003.baselines import trace_tokens
from rcdl003.contracts import TEST_EVIDENCE_HOOK
from rcdl003.metrics import score_predictions
from rcdl003.replica import run_pair
from rcdl003.tournament import held_out_examples, run_tournament


class BaselineTests(unittest.TestCase):
    def test_integer_metrics_recompute(self) -> None:
        score = score_predictions(
            (True, True, False, False),
            (True, False, True, False),
        )
        self.assertEqual(score.accuracy_ppm, 500_000)
        self.assertEqual(score.balanced_accuracy_ppm, 500_000)
        self.assertEqual(score.failure_f1_ppm, 500_000)

    def test_full_trace_tokens_exclude_direct_intervention_labels_and_hashes(self) -> None:
        trace = run_pair(TEST_EVIDENCE_HOOK, "active", 5).trace
        tokens = trace_tokens(trace)
        joined = "\n".join(tokens)
        self.assertNotIn("test_evidence_guard", joined)
        self.assertNotIn("arm", joined)
        for event in trace.events:
            patch_hash = event.get("patch_hash")
            if patch_hash:
                self.assertNotIn(patch_hash, joined)

    def test_held_out_matrix_contains_both_classes(self) -> None:
        rows = held_out_examples((10_000,))
        self.assertEqual(len(rows), 32)
        self.assertEqual({row.failed for row in rows}, {False, True})

    def test_contract_predictor_strictly_beats_declared_baselines(self) -> None:
        result = run_tournament(
            adapted_training_seeds=range(4), held_out_seeds=range(10_000, 10_004)
        )
        self.assertEqual(result["verdict"], "RCDL_STRICT_WIN")
        contract = result["rcdl_contract_predictor"]["score"]
        baseline = result["best_ordinary_score"]
        self.assertEqual(contract["balanced_accuracy_ppm"], 1_000_000)
        self.assertGreater(
            contract["balanced_accuracy_ppm"], baseline["balanced_accuracy_ppm"]
        )

    def test_tournament_keeps_stronger_model_gap_explicit(self) -> None:
        result = run_tournament(
            adapted_training_seeds=range(2), held_out_seeds=range(20_000, 20_002)
        )
        self.assertFalse(
            result["feature_boundary"]["strong_learned_sequence_or_graph_models_tested"]
        )


if __name__ == "__main__":
    unittest.main()
