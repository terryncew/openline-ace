"""Dependency-free ordinary predictors used in the baseline tournament.

These models receive traces and training labels.  They cannot access the
external oracle at prediction time, RCDL evaluations, intervention targets,
or equality/join features engineered from the frozen contract grammar.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Iterable

from rcdl.trace import Trace

from .metrics import score_predictions


@dataclass(frozen=True)
class TrainingExample:
    trace: Trace
    failed: bool


_EXCLUDED_ATTRS = {
    "arm",
    "base_hash",
    "event_id",
    "hook",
    "intervention_arm",
    "patch_hash",
    "run_id",
    "seed",
    "task_id",
}


def scalar_features(trace: Trace) -> dict[str, int]:
    kinds = Counter(event.kind for event in trace.events)
    approved = sum(event.kind == "review_decision" and event.get("approved") is True for event in trace.events)
    passed = sum(event.kind == "test_result" and event.get("passed") is True for event in trace.events)
    failed = sum(event.kind == "test_result" and event.get("passed") is False for event in trace.events)
    fresh = sum(event.kind == "workspace_observation" and event.get("fresh") is True for event in trace.events)
    stale = sum(event.kind == "workspace_observation" and event.get("fresh") is False for event in trace.events)
    return {
        "event_count": len(trace.events),
        "actor_count": len({event.node for event in trace.events}),
        "event_kind_count": len(kinds),
        "release_count": kinds["artifact_released"],
        "withheld_count": kinds["release_withheld"],
        "approval_count": approved,
        "passing_result_count": passed,
        "failing_result_count": failed,
        "fresh_observation_count": fresh,
        "stale_observation_count": stale,
        "wait_count": kinds["recovery_wait"],
    }


def graph_features(trace: Trace) -> dict[str, int]:
    transitions = list(zip(trace.events, trace.events[1:]))
    actors = {event.node for event in trace.events}
    directed_edges = {(left.node, right.node) for left, right in transitions}
    self_edges = sum(left.node == right.node for left, right in transitions)
    kinds = {event.kind for event in trace.events}
    return {
        "vertices": len(actors),
        "directed_edges": len(directed_edges),
        "transition_count": len(transitions),
        "self_transition_count": self_edges,
        "kind_vertices": len(kinds),
        "event_count": len(trace.events),
    }


def trace_tokens(trace: Trace) -> frozenset[str]:
    """Bag-of-symbols representation with direct intervention labels removed."""

    tokens: set[str] = set()
    previous: str | None = None
    for event in trace.events:
        tokens.add(f"kind:{event.kind}")
        if previous is not None:
            tokens.add(f"bigram:{previous}>{event.kind}")
        previous = event.kind
        for key, value in event.attrs.items():
            if key in _EXCLUDED_ATTRS:
                continue
            if value is None or isinstance(value, (bool, int)):
                tokens.add(f"attr:{event.kind}:{key}={value!r}")
            elif isinstance(value, str) and len(value) <= 32:
                tokens.add(f"attr:{event.kind}:{key}={value}")
    return frozenset(tokens)


class DecisionStump:
    def __init__(self, feature_fn: Callable[[Trace], dict[str, int]]) -> None:
        self.feature_fn = feature_fn
        self.rule: tuple[str, str, int] | None = None

    def fit(self, examples: Iterable[TrainingExample]) -> "DecisionStump":
        rows = tuple(examples)
        if not rows or len({row.failed for row in rows}) != 2:
            raise ValueError("stump training requires both classes")
        vectors = [self.feature_fn(row.trace) for row in rows]
        labels = [row.failed for row in rows]
        keys = sorted(set.intersection(*(set(vector) for vector in vectors)))
        candidates: list[tuple[int, int, str, str, int]] = []
        for key in keys:
            for threshold in sorted({vector[key] for vector in vectors}):
                for op in ("gt", "le"):
                    predictions = [
                        vector[key] > threshold if op == "gt" else vector[key] <= threshold
                        for vector in vectors
                    ]
                    score = score_predictions(labels, predictions)
                    candidates.append(
                        (
                            score.balanced_accuracy_ppm,
                            score.accuracy_ppm,
                            key,
                            op,
                            threshold,
                        )
                    )
        if not candidates:
            raise ValueError("no stump candidate features")
        best_score = max((item[0], item[1]) for item in candidates)
        tied = sorted(
            item for item in candidates if (item[0], item[1]) == best_score
        )
        _, _, key, op, threshold = tied[0]
        self.rule = (key, op, threshold)
        return self

    def predict(self, trace: Trace) -> bool:
        if self.rule is None:
            raise RuntimeError("stump is not fitted")
        key, op, threshold = self.rule
        value = self.feature_fn(trace)[key]
        return value > threshold if op == "gt" else value <= threshold


class NearestCentroid:
    def __init__(self, feature_fn: Callable[[Trace], dict[str, int]]) -> None:
        self.feature_fn = feature_fn
        self.centroids: dict[bool, dict[str, Fraction]] | None = None

    def fit(self, examples: Iterable[TrainingExample]) -> "NearestCentroid":
        rows = tuple(examples)
        groups = {label: [row for row in rows if row.failed is label] for label in (False, True)}
        if any(not group for group in groups.values()):
            raise ValueError("centroid training requires both classes")
        keys = sorted(
            set.intersection(*(set(self.feature_fn(row.trace)) for row in rows))
        )
        self.centroids = {
            label: {
                key: Fraction(
                    sum(self.feature_fn(row.trace)[key] for row in group), len(group)
                )
                for key in keys
            }
            for label, group in groups.items()
        }
        return self

    def predict(self, trace: Trace) -> bool:
        if self.centroids is None:
            raise RuntimeError("centroid model is not fitted")
        vector = self.feature_fn(trace)
        distances = {
            label: sum((Fraction(vector[key]) - value) ** 2 for key, value in centroid.items())
            for label, centroid in self.centroids.items()
        }
        return distances[True] < distances[False]


class BernoulliTraceNB:
    def __init__(self) -> None:
        self.class_counts: Counter[bool] = Counter()
        self.token_counts: dict[bool, Counter[str]] = {False: Counter(), True: Counter()}
        self.vocabulary: frozenset[str] = frozenset()

    def fit(self, examples: Iterable[TrainingExample]) -> "BernoulliTraceNB":
        rows = tuple(examples)
        if not rows or len({row.failed for row in rows}) != 2:
            raise ValueError("naive Bayes training requires both classes")
        vocabulary: set[str] = set()
        for row in rows:
            tokens = trace_tokens(row.trace)
            self.class_counts[row.failed] += 1
            self.token_counts[row.failed].update(tokens)
            vocabulary.update(tokens)
        self.vocabulary = frozenset(vocabulary)
        return self

    def predict(self, trace: Trace) -> bool:
        if not self.vocabulary:
            raise RuntimeError("naive Bayes model is not fitted")
        present = trace_tokens(trace)
        total = sum(self.class_counts.values())
        scores: dict[bool, float] = {}
        for label in (False, True):
            class_count = self.class_counts[label]
            score = math.log((class_count + 1) / (total + 2))
            for token in self.vocabulary:
                probability = (self.token_counts[label][token] + 1) / (class_count + 2)
                score += math.log(probability if token in present else 1 - probability)
            scores[label] = score
        return scores[True] > scores[False]
