from __future__ import annotations

from .model import Prediction


def score(prediction: Prediction, required_reopenings: frozenset[str]) -> dict[str, object]:
    predicted = prediction.reopened
    true_positive = len(predicted & required_reopenings)
    false_positive = len(predicted - required_reopenings)
    false_negative = len(required_reopenings - predicted)

    precision = true_positive / len(predicted) if predicted else (1.0 if not required_reopenings else 0.0)
    recall = true_positive / len(required_reopenings) if required_reopenings else 1.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return {
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "review_count": len(predicted),
        "true_reopenings": true_positive,
        "missed_reopenings": false_negative,
        "excess_reviews": false_positive,
    }
