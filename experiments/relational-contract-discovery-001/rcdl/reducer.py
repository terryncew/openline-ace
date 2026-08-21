"""Exhaustive inclusion-minimal family enumeration for bounded candidate sets."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from itertools import combinations


def inclusion_minimal_families(
    items: Iterable[str],
    passes: Callable[[frozenset[str]], bool],
    *,
    max_items: int = 16,
) -> tuple[frozenset[str], ...]:
    ordered = tuple(sorted(set(items)))
    if len(ordered) > max_items:
        raise ValueError(f"exhaustive reducer is bounded to {max_items} candidates")
    passing: list[frozenset[str]] = []
    for size in range(len(ordered) + 1):
        for combo in combinations(ordered, size):
            family = frozenset(combo)
            if any(existing < family for existing in passing):
                continue
            if passes(family):
                passing.append(family)
    return tuple(passing)

