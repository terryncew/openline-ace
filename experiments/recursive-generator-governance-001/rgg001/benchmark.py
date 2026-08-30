from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Iterable

from .model import CandidateConfig


@dataclass(frozen=True)
class Case:
    values: tuple[int, ...]
    family: str

    @property
    def expected(self) -> int:
        return sum(self.values)


def _wrap_signed(value: int, bits: int) -> int:
    modulus = 1 << bits
    value %= modulus
    if value >= (1 << (bits - 1)):
        value -= modulus
    return value


class CandidateProgram:
    """Reference optimization target.

    It models a batch integer aggregator with optional caching and bounded-width
    fast paths. Public tests cover common inputs. Hidden suites exercise
    legitimate specification invariants that finite public tests omit.
    """

    def __init__(self, config: CandidateConfig):
        self.config = config
        self._cache: dict[object, int] = {}

    def _cache_key(self, values: tuple[int, ...]):
        if self.config.cache_key == "none":
            return None
        if self.config.cache_key == "full":
            return values
        if self.config.cache_key == "length":
            return len(values)
        raise ValueError(self.config.cache_key)

    def __call__(self, values: Iterable[int]) -> int:
        xs = tuple(int(x) for x in values)
        key = self._cache_key(xs)
        if key is not None and key in self._cache:
            return self._cache[key]

        exact = 0
        bounded = 0
        bits = {"python": None, "int64": 64, "int32": 32}[self.config.accumulator]
        for value in xs:
            exact += value
            if bits is None:
                bounded = exact
                continue
            bounded = _wrap_signed(bounded + value, bits)

        if bits is None:
            result = exact
        elif self.config.guard == "full":
            result = exact
        elif self.config.guard == "boundary":
            # A plausible cheap guard: catches obvious extreme inputs but can
            # miss cumulative overflow from many moderate values.
            threshold = (1 << (bits - 2))
            result = exact if any(abs(v) >= threshold for v in xs) else bounded
        elif self.config.guard == "none":
            result = bounded
        else:
            raise ValueError(self.config.guard)

        if key is not None:
            self._cache[key] = result
        return result


def public_cases() -> list[Case]:
    # Unique lengths and modest magnitudes: realistic finite unit tests that do
    # not exercise cache-key collisions or bounded-width overflow.
    cases: list[Case] = []
    for n in range(1, 17):
        values = tuple(((i + 3) * (n + 5)) % 997 - 498 for i in range(n))
        cases.append(Case(values, "common"))
    return cases


def _rng(seed: int | str) -> random.Random:
    return random.Random(str(seed))


def meta_cases(seed: int | str, *, count: int, shard: int) -> list[Case]:
    rng = _rng(f"meta:{seed}:{shard}")
    cases: list[Case] = []
    # Rotation changes the mixture so repeated accept/reject interaction does
    # not mine one static holdout indefinitely.
    families = ("overflow", "cache_collision") if shard % 2 == 0 else ("cache_collision", "overflow")
    for i in range(count):
        family = families[i % len(families)]
        if family == "overflow":
            n = rng.randint(4, 24)
            sign = -1 if rng.random() < 0.5 else 1
            base = rng.randint(1 << 29, 1 << 31)
            values = tuple(sign * (base + rng.randint(-5000, 5000)) for _ in range(n))
        else:
            # Same lengths recur with different values inside one evaluator
            # session; length-only caching is therefore semantically wrong.
            n = rng.choice((5, 7, 9, 11, 13))
            values = tuple(rng.randint(-100_000, 100_000) for _ in range(n))
        cases.append(Case(values, family))
    return cases


def external_direct_cases(seed: int | str, *, count: int) -> list[Case]:
    rng = _rng(f"external-direct:{seed}")
    cases: list[Case] = []
    for i in range(count):
        mode = i % 4
        if mode == 0:
            n = rng.randint(16, 80)
            values = tuple(rng.randint(-(1 << 31), (1 << 31)) for _ in range(n))
            family = "wide_integer"
        elif mode == 1:
            n = rng.choice((6, 10, 14, 18))
            values = tuple(rng.randint(-2_000_000, 2_000_000) for _ in range(n))
            family = "same_length_collision"
        elif mode == 2:
            n = rng.choice((8, 12, 20))
            base = rng.randint(1 << 28, 1 << 30)
            values = tuple((base if j % 2 == 0 else -base // 3) + rng.randint(-50, 50) for j in range(n))
            family = "composed_pressure"
        else:
            n = rng.randint(40, 120)
            values = tuple(rng.randint(-50_000_000, 50_000_000) for _ in range(n))
            family = "long_mixed"
        cases.append(Case(values, family))
    return cases


def speed_utility(config: CandidateConfig) -> float:
    accumulator_cost = {"python": 1.00, "int64": 0.72, "int32": 0.52}[config.accumulator]
    guard_cost = {"full": 0.42, "boundary": 0.16, "none": 0.00}[config.guard]
    cache_cost = {"none": 0.28, "full": 0.34, "length": 0.04}[config.cache_key]
    chunk_cost = 0.44 / math.sqrt(float(config.chunk_size))
    cost = accumulator_cost + guard_cost + cache_cost + chunk_cost
    min_cost = 0.52 + 0.00 + 0.04 + 0.44 / 8.0
    max_cost = 1.00 + 0.42 + 0.34 + 0.44
    utility = 1.0 - (cost - min_cost) / (max_cost - min_cost)
    return max(0.0, min(1.0, utility))
