"""Frozen-corpus tournament: RCDL contracts versus learned relations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from rcdl.evaluator import evaluate
from rcdl.model import Clause
from rcdl.trace import Trace

from .bindings import verify_frozen_bindings
from .corpus import FrozenCorpus, LearningExample, load_frozen_corpus
from .features import FEATURE_EXTRACTORS, feature_schema_digest, sequence_features, task_segments
from .metrics import ClassificationScore, score_predictions
from .models import (
    FeatureRow,
    HighPrecisionRelationalRuleSet,
    MarginPerceptron,
    RelationalDecisionTree,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = EXPERIMENT_ROOT.parent / "relational-contract-discovery-003"
TARGET_CLAUSE_IDS = frozenset(
    {
        "workflow.test_result_matches_patch",
        "workflow.review_inspects_current_patch",
        "workflow.approval_requires_passing_tests",
        "workflow.recovery_requires_fresh_observation",
    }
)


@dataclass(frozen=True)
class PreparedExample:
    example_id: str
    failed: bool
    features: dict[str, int]


def _score(rows: Iterable[PreparedExample], predictor: Callable[[dict[str, int]], bool]) -> ClassificationScore:
    materialized = tuple(rows)
    return score_predictions(
        (row.failed for row in materialized),
        (predictor(row.features) for row in materialized),
    )


def _feature_rows(rows: Iterable[PreparedExample]) -> tuple[FeatureRow, ...]:
    return tuple(FeatureRow(row.features, row.failed) for row in rows)


def _prepare(
    corpus: FrozenCorpus, split: str, extractor: Callable[[Trace], dict[str, int]]
) -> tuple[PreparedExample, ...]:
    return tuple(
        PreparedExample(row.example_id, row.failed, extractor(row.trace))
        for row in corpus.split(split)
    )


def _score_key(score: ClassificationScore) -> tuple[int, int, int]:
    return (score.balanced_accuracy_ppm, score.failure_f1_ppm, score.accuracy_ppm)


def _fit_tree(
    *,
    representation: str,
    corpus: FrozenCorpus,
    candidates: tuple[tuple[int, int], ...],
) -> tuple[dict[str, Any], dict[str, bool]]:
    extractor = FEATURE_EXTRACTORS[representation]
    train = _prepare(corpus, "train", extractor)
    validation = _prepare(corpus, "validation", extractor)
    test = _prepare(corpus, "test", extractor)
    selected: tuple[tuple[tuple[int, int, int], int], int, int, ClassificationScore] | None = None
    for order, (max_depth, min_leaf) in enumerate(candidates):
        model = RelationalDecisionTree(max_depth=max_depth, min_leaf=min_leaf).fit(
            _feature_rows(train)
        )
        score = _score(validation, model.predict)
        key = (_score_key(score), -order)
        if selected is None or key > selected[0]:
            selected = (key, max_depth, min_leaf, score)
    if selected is None:  # pragma: no cover
        raise RuntimeError("tree model selection produced no candidate")
    _, max_depth, min_leaf, validation_score = selected
    fitted = RelationalDecisionTree(max_depth=max_depth, min_leaf=min_leaf).fit(
        _feature_rows((*train, *validation))
    )
    predictions = {row.example_id: fitted.predict(row.features) for row in test}
    test_score = score_predictions(
        (row.failed for row in test), (predictions[row.example_id] for row in test)
    )
    return (
        {
            "algorithm": "deterministic_relational_decision_tree",
            "representation": representation,
            "hyperparameters": {"max_depth": max_depth, "min_leaf": min_leaf},
            "selection_candidates": [
                {"max_depth": depth, "min_leaf": leaf} for depth, leaf in candidates
            ],
            "training_examples": len(train),
            "validation_examples": len(validation),
            "test_examples": len(test),
            "validation_score": validation_score.to_dict(),
            "test_score": test_score.to_dict(),
            "fitted_feature_count": fitted.feature_count,
            "fitted_depth": fitted.depth(),
        },
        predictions,
    )


def _fit_task_bag_tree(
    *, corpus: FrozenCorpus, candidates: tuple[tuple[int, int], ...]
) -> tuple[dict[str, Any], dict[str, bool]]:
    """Learn per-task relations, then apply a declared any-failure aggregator."""

    train_examples = corpus.split("train")
    validation_examples = corpus.split("validation")
    test_examples = corpus.split("test")

    def single_segment_rows(examples: tuple[LearningExample, ...]) -> tuple[PreparedExample, ...]:
        rows: list[PreparedExample] = []
        for example in examples:
            segments = task_segments(example.trace)
            if len(segments) != 1:
                raise RuntimeError("task-bag training requires single-task traces")
            rows.append(
                PreparedExample(example.example_id, example.failed, sequence_features(segments[0]))
            )
        return tuple(rows)

    train = single_segment_rows(train_examples)
    validation = single_segment_rows(validation_examples)
    selected: tuple[tuple[tuple[int, int, int], int], int, int, ClassificationScore] | None = None
    for order, (max_depth, min_leaf) in enumerate(candidates):
        model = RelationalDecisionTree(max_depth=max_depth, min_leaf=min_leaf).fit(
            _feature_rows(train)
        )
        score = _score(validation, model.predict)
        key = (_score_key(score), -order)
        if selected is None or key > selected[0]:
            selected = (key, max_depth, min_leaf, score)
    if selected is None:  # pragma: no cover
        raise RuntimeError("task-bag model selection produced no candidate")
    _, max_depth, min_leaf, validation_score = selected
    fitted = RelationalDecisionTree(max_depth=max_depth, min_leaf=min_leaf).fit(
        _feature_rows((*train, *validation))
    )
    predictions = {
        example.example_id: any(
            fitted.predict(sequence_features(segment))
            for segment in task_segments(example.trace)
        )
        for example in test_examples
    }
    test_score = score_predictions(
        (example.failed for example in test_examples),
        (predictions[example.example_id] for example in test_examples),
    )
    return (
        {
            "algorithm": "deterministic_multiple_instance_relational_tree",
            "representation": "opaque_task_bag_of_generic_relational_sequences",
            "aggregation": "any_segment_failure",
            "hyperparameters": {"max_depth": max_depth, "min_leaf": min_leaf},
            "selection_candidates": [
                {"max_depth": depth, "min_leaf": leaf} for depth, leaf in candidates
            ],
            "training_examples": len(train),
            "validation_examples": len(validation),
            "test_examples": len(test_examples),
            "validation_score": validation_score.to_dict(),
            "test_score": test_score.to_dict(),
            "fitted_feature_count": fitted.feature_count,
            "fitted_depth": fitted.depth(),
            "structural_prior": "global_failure_if_any_opaque_task_segment_is_predicted_failed",
        },
        predictions,
    )


def _fit_task_bag_rules(
    *, corpus: FrozenCorpus, support_candidates: tuple[int, ...]
) -> tuple[dict[str, Any], dict[str, bool]]:
    """Learn a compact high-precision DNF and aggregate opaque task bags."""

    def rows(examples: tuple[LearningExample, ...]) -> tuple[PreparedExample, ...]:
        prepared: list[PreparedExample] = []
        for example in examples:
            segments = task_segments(example.trace)
            if len(segments) != 1:
                raise RuntimeError("rule-set training requires single-task traces")
            prepared.append(
                PreparedExample(example.example_id, example.failed, sequence_features(segments[0]))
            )
        return tuple(prepared)

    train = rows(corpus.split("train"))
    validation = rows(corpus.split("validation"))
    selected_support: int | None = None
    selected_score: ClassificationScore | None = None
    selected_model: HighPrecisionRelationalRuleSet | None = None
    for support in support_candidates:
        model = HighPrecisionRelationalRuleSet(min_support=support).fit(_feature_rows(train))
        score = _score(validation, model.predict)
        if selected_score is None or _score_key(score) > _score_key(selected_score):
            selected_support = support
            selected_score = score
            selected_model = model
    if selected_support is None or selected_score is None or selected_model is None:  # pragma: no cover
        raise RuntimeError("rule-set model selection produced no candidate")
    fitted = selected_model
    test_examples = corpus.split("test")
    predictions = {
        example.example_id: any(
            fitted.predict(sequence_features(segment))
            for segment in task_segments(example.trace)
        )
        for example in test_examples
    }
    test_score = score_predictions(
        (example.failed for example in test_examples),
        (predictions[example.example_id] for example in test_examples),
    )
    return (
        {
            "algorithm": "deterministic_minimum_description_relational_dnf",
            "representation": "opaque_task_bag_of_generic_relational_sequences",
            "aggregation": "any_segment_failure",
            "hyperparameters": {
                "min_positive_support": selected_support,
                "max_rule_size": 2,
                "max_negative_support": 0,
                "tie_policy": "retain_all_minimum_cost_explanations",
            },
            "selection_candidates": [
                {
                    "min_positive_support": support,
                    "max_rule_size": 2,
                    "max_negative_support": 0,
                    "tie_policy": "retain_all_minimum_cost_explanations",
                }
                for support in support_candidates
            ],
            "training_examples": len(train),
            "validation_examples": len(validation),
            "test_examples": len(test_examples),
            "validation_score": selected_score.to_dict(),
            "test_score": test_score.to_dict(),
            "fitted_feature_count": fitted.feature_count,
            "fitted_rule_count": len(fitted.rules),
            "fitted_rules": [list(rule) for rule in fitted.rules],
            "covered_training_positives": fitted.covered_positive_examples,
            "training_positives": fitted.positive_examples,
            "structural_prior": "global_failure_if_any_opaque_task_segment_is_predicted_failed",
        },
        predictions,
    )
def _fit_perceptron(
    *,
    representation: str,
    corpus: FrozenCorpus,
    epochs_candidates: tuple[int, ...],
) -> tuple[dict[str, Any], dict[str, bool]]:
    extractor = FEATURE_EXTRACTORS[representation]
    train = _prepare(corpus, "train", extractor)
    validation = _prepare(corpus, "validation", extractor)
    test = _prepare(corpus, "test", extractor)
    selected_epochs: int | None = None
    selected_score: ClassificationScore | None = None
    for epochs in epochs_candidates:
        model = MarginPerceptron(epochs=epochs, margin=1).fit(_feature_rows(train))
        score = _score(validation, model.predict)
        if selected_score is None or _score_key(score) > _score_key(selected_score):
            selected_epochs = epochs
            selected_score = score
    if selected_epochs is None or selected_score is None:  # pragma: no cover
        raise RuntimeError("perceptron model selection produced no candidate")
    fitted = MarginPerceptron(epochs=selected_epochs, margin=1).fit(
        _feature_rows((*train, *validation))
    )
    predictions = {row.example_id: fitted.predict(row.features) for row in test}
    test_score = score_predictions(
        (row.failed for row in test), (predictions[row.example_id] for row in test)
    )
    return (
        {
            "algorithm": "deterministic_sparse_margin_perceptron",
            "representation": representation,
            "hyperparameters": {"epochs": selected_epochs, "margin": 1},
            "selection_candidates": [{"epochs": epochs, "margin": 1} for epochs in epochs_candidates],
            "training_examples": len(train),
            "validation_examples": len(validation),
            "test_examples": len(test),
            "validation_score": selected_score.to_dict(),
            "test_score": test_score.to_dict(),
            "fitted_feature_count": fitted.feature_count,
        },
        predictions,
    )


def _frozen_target_clauses() -> tuple[Clause, ...]:
    clauses = tuple(Clause.from_path(path) for path in sorted((SOURCE_ROOT / "clauses").glob("*.json")))
    selected = tuple(clause for clause in clauses if clause.id in TARGET_CLAUSE_IDS)
    if len(selected) != 4 or {clause.id for clause in selected} != TARGET_CLAUSE_IDS:
        raise RuntimeError("frozen target-clause family changed")
    return selected


def _rcdl_predictions(rows: tuple[LearningExample, ...]) -> dict[str, bool]:
    clauses = _frozen_target_clauses()
    return {
        row.example_id: any(not evaluate(clause, row.trace).passed for clause in clauses)
        for row in rows
    }


def _scientific_verdict(
    rcdl_score: ClassificationScore, best_score: ClassificationScore
) -> str:
    rcdl_key = (rcdl_score.balanced_accuracy_ppm, rcdl_score.failure_f1_ppm)
    learned_key = (best_score.balanced_accuracy_ppm, best_score.failure_f1_ppm)
    if rcdl_key == learned_key:
        return "LEARNED_PARITY"
    if rcdl_score.balanced_accuracy_ppm > best_score.balanced_accuracy_ppm and rcdl_score.failure_f1_ppm >= best_score.failure_f1_ppm:
        return "RCDL_STRICT_WIN"
    if best_score.balanced_accuracy_ppm > rcdl_score.balanced_accuracy_ppm and best_score.failure_f1_ppm >= rcdl_score.failure_f1_ppm:
        return "LEARNED_STRICT_WIN"
    return "MIXED_RESULT"


def run_tournament() -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    binding = verify_frozen_bindings()
    corpus = load_frozen_corpus()
    model_outputs: list[tuple[str, dict[str, Any], dict[str, bool]]] = []
    record, predictions = _fit_tree(
        representation="generic_relational_sequence",
        corpus=corpus,
        candidates=((4, 4), (6, 4), (8, 4), (6, 8)),
    )
    model_outputs.append(("relational_sequence_tree", record, predictions))
    record, predictions = _fit_tree(
        representation="weisfeiler_lehman_event_graph",
        corpus=corpus,
        candidates=((4, 4), (6, 4), (8, 4), (6, 8)),
    )
    model_outputs.append(("wl_event_graph_tree", record, predictions))
    record, predictions = _fit_perceptron(
        representation="combined_sequence_graph",
        corpus=corpus,
        epochs_candidates=(4, 8, 16, 32),
    )
    model_outputs.append(("combined_relational_margin_model", record, predictions))
    record, predictions = _fit_task_bag_tree(
        corpus=corpus,
        candidates=((4, 4), (6, 4), (8, 4), (6, 8)),
    )
    model_outputs.append(("task_bag_relational_tree", record, predictions))
    record, predictions = _fit_task_bag_rules(
        corpus=corpus,
        support_candidates=(32,),
    )
    model_outputs.append(("task_bag_relational_rule_set", record, predictions))

    models = []
    all_predictions: dict[str, dict[str, bool]] = {}
    for name, record, predictions in model_outputs:
        models.append({"name": name, **record})
        all_predictions[name] = predictions
    models.sort(key=lambda item: str(item["name"]))
    best = max(
        models,
        key=lambda item: (
            item["test_score"]["balanced_accuracy_ppm"],
            item["test_score"]["failure_f1_ppm"],
            item["test_score"]["accuracy_ppm"],
            str(item["name"]),
        ),
    )
    test_rows = corpus.split("test")
    rcdl_predictions = _rcdl_predictions(test_rows)
    rcdl_score = score_predictions(
        (row.failed for row in test_rows),
        (rcdl_predictions[row.example_id] for row in test_rows),
    )
    best_score = ClassificationScore(
        best["test_score"]["true_positive"],
        best["test_score"]["true_negative"],
        best["test_score"]["false_positive"],
        best["test_score"]["false_negative"],
    )
    verdict = _scientific_verdict(rcdl_score, best_score)
    prediction_rows = tuple(
        {
            "schema": "rcdl.pressure-test-prediction/0.1",
            "example_id": row.example_id,
            "failed": row.failed,
            "rcdl_prediction": rcdl_predictions[row.example_id],
            "learned_predictions": {
                name: all_predictions[name][row.example_id] for name in sorted(all_predictions)
            },
        }
        for row in test_rows
    )
    tournament = {
        "schema": "rcdl.learned-baseline-tournament/0.1",
        "question": "Can generic learned sequence or graph relations match the frozen RCDL contract predictor?",
        "protocol_status": "VALID_RESULT",
        "scientific_verdict": verdict,
        "corpus": corpus.to_dict(),
        "bindings": binding.to_dict(),
        "feature_schema_digest": feature_schema_digest(),
        "information_boundary": {
            "training_labels_available": True,
            "validation_labels_used_for_model_selection": True,
            "test_labels_hidden_until_scoring": True,
            "clause_definitions_available_to_learned_models": False,
            "intervention_or_hook_labels_available": False,
            "oracle_available_at_prediction": False,
            "raw_artifact_or_task_identities_available": False,
            "generic_cross_event_equality_available": True,
            "opaque_task_equality_available": True,
        },
        "rcdl_contract_predictor": {
            "frozen_clause_count": 4,
            "training_examples": 0,
            "test_score": rcdl_score.to_dict(),
        },
        "learned_models": models,
        "best_learned_model": best["name"],
        "best_learned_score": best["test_score"],
        "model_boundary": {
            "sequence_model_tested": True,
            "graph_model_tested": True,
            "multiple_instance_model_tested": True,
            "neural_models_tested": False,
            "external_hyperparameter_search": False,
            "independent_developer_or_lab": False,
        },
    }
    return tournament, prediction_rows
