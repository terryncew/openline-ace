from __future__ import annotations

import hashlib
import random
from typing import Iterable, Sequence


def _percentile(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("empty percentile input")
    if q <= 0:
        return sorted_values[0]
    if q >= 1:
        return sorted_values[-1]
    position = q * (len(sorted_values) - 1)
    lo = int(position)
    hi = min(lo + 1, len(sorted_values) - 1)
    fraction = position - lo
    return sorted_values[lo] * (1.0 - fraction) + sorted_values[hi] * fraction


def paired_bootstrap_mean_ci(
    values: Sequence[float],
    *,
    samples: int,
    alpha: float,
    seed_material: str,
) -> tuple[float, float, float]:
    if not values:
        raise ValueError("no paired values")
    if samples < 100:
        raise ValueError("bootstrap samples too small")
    if not 0.0 < alpha < 1.0:
        raise ValueError("invalid alpha")
    n = len(values)
    mean = sum(values) / n
    seed = int.from_bytes(
        hashlib.sha256(seed_material.encode("utf-8")).digest()[:8], "big"
    )
    rng = random.Random(seed)
    draws: list[float] = []
    for _ in range(samples):
        total = 0.0
        for _ in range(n):
            total += values[rng.randrange(n)]
        draws.append(total / n)
    draws.sort()
    return mean, _percentile(draws, alpha / 2), _percentile(draws, 1 - alpha / 2)
