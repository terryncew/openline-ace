"""Bounded candidate filtering.

The domain supplies finite candidate templates and actuators. This module sees
successful traces, never oracle labels, and rejects candidates without positive
support or with an observed baseline violation.
"""

from __future__ import annotations

from dataclasses import dataclass

from .evaluator import evaluate
from .model import Clause
from .trace import Trace


@dataclass(frozen=True)
class MiningResult:
    clause: Clause
    accepted: bool
    trigger_count: int
    support_count: int
    violation_count: int
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "clause_id": self.clause.id,
            "clause_digest": self.clause.digest,
            "accepted": self.accepted,
            "trigger_count": self.trigger_count,
            "support_count": self.support_count,
            "violation_count": self.violation_count,
            "reason": self.reason,
        }


def filter_candidates(
    candidates: tuple[Clause, ...],
    successful_traces: tuple[Trace, ...],
    *,
    min_support: int = 2,
) -> tuple[MiningResult, ...]:
    if not candidates:
        raise ValueError("candidate hypothesis space must not be empty")
    if len(candidates) > 256:
        raise ValueError("candidate hypothesis space is bounded to 256 clauses")
    if len({item.id for item in candidates}) != len(candidates):
        raise ValueError("candidate identifiers must be unique")
    if not successful_traces:
        raise ValueError("at least one successful trace is required")
    if len(successful_traces) > 4096:
        raise ValueError("candidate mining is bounded to 4096 traces")
    if isinstance(min_support, bool) or not isinstance(min_support, int) or min_support < 1:
        raise ValueError("minimum support must be a positive integer")
    results: list[MiningResult] = []
    for clause in candidates:
        evaluations = [evaluate(clause, trace) for trace in successful_traces]
        triggers = sum(item.trigger_count for item in evaluations)
        support = sum(item.support_count for item in evaluations)
        violations = sum(item.violation_count for item in evaluations)
        if violations:
            accepted = False
            reason = "baseline_violation"
        elif support < min_support:
            accepted = False
            reason = "insufficient_positive_support"
        else:
            accepted = True
            reason = "no_baseline_violations_with_positive_support"
        results.append(MiningResult(clause, accepted, triggers, support, violations, reason))
    return tuple(results)
