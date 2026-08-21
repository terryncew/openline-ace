"""Integer classification metrics for deterministic evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

PPM = 1_000_000


@dataclass(frozen=True)
class ClassificationScore:
    true_positive: int
    true_negative: int
    false_positive: int
    false_negative: int

    @property
    def total(self) -> int:
        return self.true_positive + self.true_negative + self.false_positive + self.false_negative

    @property
    def accuracy_ppm(self) -> int:
        return (self.true_positive + self.true_negative) * PPM // self.total

    @property
    def balanced_accuracy_ppm(self) -> int:
        positives = self.true_positive + self.false_negative
        negatives = self.true_negative + self.false_positive
        if not positives or not negatives:
            raise ValueError("balanced accuracy requires both outcome classes")
        sensitivity = self.true_positive * PPM // positives
        specificity = self.true_negative * PPM // negatives
        return (sensitivity + specificity) // 2

    @property
    def failure_f1_ppm(self) -> int:
        denominator = 2 * self.true_positive + self.false_positive + self.false_negative
        return 0 if not denominator else 2 * self.true_positive * PPM // denominator

    def to_dict(self) -> dict[str, int]:
        return {
            "true_positive": self.true_positive,
            "true_negative": self.true_negative,
            "false_positive": self.false_positive,
            "false_negative": self.false_negative,
            "accuracy_ppm": self.accuracy_ppm,
            "balanced_accuracy_ppm": self.balanced_accuracy_ppm,
            "failure_f1_ppm": self.failure_f1_ppm,
        }


def score_predictions(
    labels: Iterable[bool], predictions: Iterable[bool]
) -> ClassificationScore:
    expected = tuple(labels)
    observed = tuple(predictions)
    if not expected or len(expected) != len(observed):
        raise ValueError("labels and predictions must have the same non-zero length")
    tp = sum(label and prediction for label, prediction in zip(expected, observed))
    tn = sum(not label and not prediction for label, prediction in zip(expected, observed))
    fp = sum(not label and prediction for label, prediction in zip(expected, observed))
    fn = sum(label and not prediction for label, prediction in zip(expected, observed))
    return ClassificationScore(tp, tn, fp, fn)
