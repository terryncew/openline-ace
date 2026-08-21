"""Held-out cross-implementation baseline tournament."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Callable, Iterable

from rcdl.evaluator import evaluate
from rcdl.nuisance import nuisance_variants
from rcdl.otel import trace_from_otlp, trace_to_otlp
from rcdl.trace import Trace

from .baselines import (
    BernoulliTraceNB,
    DecisionStump,
    NearestCentroid,
    TrainingExample,
    graph_features,
    scalar_features,
)
from .contracts import (
    PLANNER_NOTE_HOOK,
    SPURIOUS_CONTROL_IDS,
    TARGET_CLAUSE_IDS,
    clauses_by_id,
    frozen_clauses,
)
from .metrics import ClassificationScore, score_predictions
from .oracle import check_external_behavior
from .replica import LedgerRun, run_batch, run_pair

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class EvaluationExample:
    name: str
    trace: Trace
    failed: bool


def _source_examples() -> tuple[TrainingExample, ...]:
    root = EXPERIMENT_ROOT / "references" / "source-baseline"
    rows: list[TrainingExample] = []
    for path in sorted(root.glob("*.json")):
        parts = path.name.removesuffix(".json").rsplit(".", 1)
        if len(parts) != 2 or parts[1] not in {"active", "sham"}:
            raise ValueError(f"invalid source-baseline trace name: {path.name}")
        clause_id, arm = parts
        failed = arm == "active" and clause_id in TARGET_CLAUSE_IDS
        rows.append(TrainingExample(Trace.from_path(path), failed))
    if len(rows) != 10:
        raise ValueError("source-baseline snapshot must contain ten traces")
    return tuple(rows)


def _adapted_examples(seeds: Iterable[int]) -> tuple[TrainingExample, ...]:
    rows: list[TrainingExample] = []
    for seed in seeds:
        for clause in frozen_clauses():
            for arm in ("active", "sham"):
                run = run_pair(clause.hook, arm, seed)
                rows.append(
                    TrainingExample(
                        run.trace, not check_external_behavior(run.outcome).passed
                    )
                )
    return tuple(rows)


def _held_out_hook_sets() -> tuple[tuple[str, ...], ...]:
    by_id = clauses_by_id()
    target_hooks = sorted(by_id[item].hook for item in TARGET_CLAUSE_IDS)
    sets: set[tuple[str, ...]] = set(combinations(target_hooks, 2))
    sets.update(combinations(target_hooks, 3))
    sets.update(tuple(sorted((hook, PLANNER_NOTE_HOOK))) for hook in target_hooks)
    sets.add(tuple(target_hooks))
    sets.add((PLANNER_NOTE_HOOK,))
    return tuple(sorted(sets))


def _variant(trace: Trace, index: int) -> Trace:
    variants = (trace, *nuisance_variants(trace), trace_from_otlp(trace_to_otlp(trace)))
    return variants[index % len(variants)]


def held_out_examples(seeds: Iterable[int]) -> tuple[EvaluationExample, ...]:
    rows: list[EvaluationExample] = []
    hook_sets = _held_out_hook_sets()
    index = 0
    for seed in seeds:
        for hooks in hook_sets:
            for active in (True, False):
                run = run_batch(hooks, active_hooks=hooks if active else (), seed=seed)
                report = check_external_behavior(run.outcome)
                rows.append(
                    EvaluationExample(
                        f"heldout-{seed}-{index}",
                        _variant(run.trace, index),
                        not report.passed,
                    )
                )
                index += 1
    return tuple(rows)


def _score(
    examples: tuple[EvaluationExample, ...], predictor: Callable[[Trace], bool]
) -> ClassificationScore:
    return score_predictions(
        (row.failed for row in examples), (predictor(row.trace) for row in examples)
    )


def _contract_predictor(trace: Trace) -> bool:
    clauses = clauses_by_id()
    return any(not evaluate(clauses[item], trace).passed for item in TARGET_CLAUSE_IDS)


def _correlational_predictor(trace: Trace) -> bool:
    # Every source-supported temporal invariant is treated as causal, including
    # the planted planner-note rule.  This is the intended correlational control.
    return any(not evaluate(clause, trace).passed for clause in frozen_clauses())


def _fit_models(examples: tuple[TrainingExample, ...]) -> dict[str, object]:
    return {
        "scalar_task_score_stump": DecisionStump(scalar_features).fit(examples),
        "graph_stat_centroid": NearestCentroid(graph_features).fit(examples),
        "full_trace_bernoulli_nb": BernoulliTraceNB().fit(examples),
    }


def run_tournament(
    *, adapted_training_seeds: Iterable[int], held_out_seeds: Iterable[int]
) -> dict[str, object]:
    source_training = _source_examples()
    adapted_training = _adapted_examples(adapted_training_seeds)
    test = held_out_examples(held_out_seeds)
    labels = {row.failed for row in test}
    if labels != {False, True}:
        raise RuntimeError("held-out tournament lost one outcome class")

    results: list[dict[str, object]] = []
    for prefix, training in (
        ("source_trained", source_training),
        ("target_adapted", adapted_training),
    ):
        for name, model in sorted(_fit_models(training).items()):
            score = _score(test, model.predict)  # type: ignore[attr-defined]
            results.append(
                {
                    "name": f"{prefix}.{name}",
                    "training_examples": len(training),
                    "uses_oracle_at_prediction": False,
                    "uses_contract_relations": False,
                    "score": score.to_dict(),
                }
            )

    correlational = _score(test, _correlational_predictor)
    results.append(
        {
            "name": "temporal_invariants_without_interventions",
            "training_examples": len(source_training),
            "uses_oracle_at_prediction": False,
            "uses_contract_relations": True,
            "causal_pruning": False,
            "score": correlational.to_dict(),
        }
    )
    results.sort(key=lambda item: str(item["name"]))
    contract_score = _score(test, _contract_predictor)
    best = max(
        results,
        key=lambda item: (
            item["score"]["balanced_accuracy_ppm"],  # type: ignore[index]
            item["score"]["failure_f1_ppm"],  # type: ignore[index]
            item["score"]["accuracy_ppm"],  # type: ignore[index]
            str(item["name"]),
        ),
    )
    best_score = best["score"]  # type: ignore[assignment]
    strict_win = (
        contract_score.balanced_accuracy_ppm
        > best_score["balanced_accuracy_ppm"]  # type: ignore[index]
        and contract_score.failure_f1_ppm
        >= best_score["failure_f1_ppm"]  # type: ignore[index]
    )
    parity = (
        contract_score.balanced_accuracy_ppm
        == best_score["balanced_accuracy_ppm"]  # type: ignore[index]
        and contract_score.failure_f1_ppm
        == best_score["failure_f1_ppm"]  # type: ignore[index]
    )
    verdict = "RCDL_STRICT_WIN" if strict_win else "RCDL_PARITY" if parity else "RCDL_NOT_BEST"
    return {
        "schema": "rcdl.baseline-tournament/0.1",
        "prediction_target": "external_behavior_failure",
        "source_training_examples": len(source_training),
        "adapted_training_examples": len(adapted_training),
        "held_out_examples": len(test),
        "held_out_perturbation_sets": len(_held_out_hook_sets()),
        "held_out_representation_variants": 5,
        "feature_boundary": {
            "direct_intervention_labels_removed": True,
            "oracle_values_unavailable_at_prediction": True,
            "hash_equality_features_unavailable_to_ordinary_models": True,
            "strong_learned_sequence_or_graph_models_tested": False,
        },
        "rcdl_contract_predictor": {
            "training_examples_in_replica": 0,
            "frozen_clause_count": len(TARGET_CLAUSE_IDS),
            "score": contract_score.to_dict(),
        },
        "ordinary_baselines": results,
        "best_ordinary_baseline": str(best["name"]),
        "best_ordinary_score": best_score,
        "verdict": verdict,
    }
