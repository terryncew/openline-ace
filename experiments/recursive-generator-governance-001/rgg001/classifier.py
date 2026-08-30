from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from math import fsum
from typing import Iterable

from .model import Classification, MutationProposal


CONSTITUTIONAL_PREFIXES = (
    "constitutional.",
    "evaluator.meta.",
    "principal.",
)
GENERATOR_PREFIXES = (
    "generator.",
    "search.",
    "scoring.",
    "retrieval.",
    "prompt_template.",
    "benchmark_adapter.",
    "shared.",
)
OPERATIONAL_PREFIXES = (
    "candidate.",
    "task.local.",
)


def classify_mutation(proposal: MutationProposal) -> Classification:
    targets = tuple(str(t) for t in proposal.targets)

    if proposal.constitutional or any(
        t.startswith(CONSTITUTIONAL_PREFIXES) for t in targets
    ):
        effective = "TIER3_CONSTITUTIONAL"
        reason = "constitutional evaluator or principal-owned surface"
    elif (
        proposal.persistent
        or proposal.shared
        or proposal.affects_future_proposals
        or any(t.startswith(GENERATOR_PREFIXES) for t in targets)
    ):
        effective = "TIER2_GENERATOR"
        reason = "persistent/shared/proposal-shaping surface defaults to Generator Gate"
    elif targets and all(t.startswith(OPERATIONAL_PREFIXES) for t in targets):
        effective = "TIER1_OPERATIONAL"
        reason = "ephemeral candidate-local mutation"
    else:
        effective = "TIER2_GENERATOR"
        reason = "unknown mutation surface defaults conservatively to Generator Gate"

    declared_map = {
        "TIER1": "TIER1_OPERATIONAL",
        "TIER2": "TIER2_GENERATOR",
        "TIER3": "TIER3_CONSTITUTIONAL",
        "TIER1_OPERATIONAL": "TIER1_OPERATIONAL",
        "TIER2_GENERATOR": "TIER2_GENERATOR",
        "TIER3_CONSTITUTIONAL": "TIER3_CONSTITUTIONAL",
    }
    declared = declared_map.get(proposal.declared_tier, proposal.declared_tier)
    laundering = declared == "TIER1_OPERATIONAL" and effective != declared
    return Classification(effective, reason, laundering)


def total_variation(left: dict[str, float], right: dict[str, float]) -> float:
    keys = set(left) | set(right)
    return 0.5 * fsum(abs(float(left.get(k, 0.0)) - float(right.get(k, 0.0))) for k in keys)


@dataclass
class DriftObservation:
    generation: int
    distribution: dict[str, float]


class CumulativeDriftAuditor:
    """Escalates cumulative proposal-distribution drift independent of declared tier.

    This catches many individually-small changes that collectively reshape the
    future proposal distribution. It is intentionally behavioral rather than
    label-based: the declaration cannot turn off the audit.
    """

    def __init__(self, *, baseline: dict[str, float], window: int, tv_threshold: float):
        if window < 2:
            raise ValueError("window must be >=2")
        self.baseline = dict(baseline)
        self.window = int(window)
        self.tv_threshold = float(tv_threshold)
        self._history: deque[DriftObservation] = deque(maxlen=self.window)

    def observe(self, generation: int, samples: Iterable[str]) -> dict:
        counts = Counter(str(x) for x in samples)
        total = sum(counts.values())
        distribution = {
            key: counts.get(key, 0) / total for key in sorted(set(self.baseline) | set(counts))
        } if total else dict(self.baseline)
        self._history.append(DriftObservation(int(generation), distribution))

        current_tv = total_variation(self.baseline, distribution)
        rolling_tv = current_tv
        if len(self._history) >= 2:
            avg: dict[str, float] = {}
            keys = set().union(*(o.distribution.keys() for o in self._history))
            for key in keys:
                avg[key] = sum(o.distribution.get(key, 0.0) for o in self._history) / len(self._history)
            rolling_tv = total_variation(self.baseline, avg)

        escalated = len(self._history) == self.window and rolling_tv >= self.tv_threshold
        return {
            "generation": int(generation),
            "current_tv": current_tv,
            "rolling_tv": rolling_tv,
            "window_full": len(self._history) == self.window,
            "escalate_to": "TIER2_GENERATOR" if escalated else None,
        }
