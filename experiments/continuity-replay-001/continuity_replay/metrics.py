from __future__ import annotations
from .model import ReplayPrediction

def score(prediction: ReplayPrediction, warranted: frozenset[str]) -> dict[str, object]:
    tp = len(prediction.reopened & warranted)
    fp = len(prediction.reopened - warranted)
    fn = len(warranted - prediction.reopened)
    precision = 1.0 if not prediction.reopened else tp / len(prediction.reopened)
    recall = 1.0 if not warranted else tp / len(warranted)
    f1 = 0.0 if precision + recall == 0.0 else 2.0 * precision * recall / (precision + recall)
    return {
        "review_count": len(prediction.reopened),
        "true_reopenings": tp,
        "excess_reviews": fp,
        "missed_reopenings": fn,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
    }
