from __future__ import annotations

import math
import random
from dataclasses import dataclass
from itertools import product
from statistics import mean, pstdev
from typing import Iterable

ACCUMULATORS = ("python", "int64", "int32")
GUARDS = ("full", "boundary", "none")
CACHE_KEYS = ("none", "full", "length")
CHUNK_SIZES = (1, 4, 16, 64)


@dataclass(frozen=True)
class Config:
    accumulator: str
    guard: str
    cache_key: str
    chunk_size: int


@dataclass(frozen=True)
class Case:
    values: tuple[int, ...]

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
    def __init__(self, config: Config):
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
            else:
                bounded = _wrap_signed(bounded + value, bits)
        if bits is None:
            result = exact
        elif self.config.guard == "full":
            result = exact
        elif self.config.guard == "boundary":
            threshold = 1 << (bits - 2)
            result = exact if any(abs(v) >= threshold for v in xs) else bounded
        elif self.config.guard == "none":
            result = bounded
        else:
            raise ValueError(self.config.guard)
        if key is not None:
            self._cache[key] = result
        return result


def speed_utility(config: Config) -> float:
    accumulator_cost = {"python": 1.00, "int64": 0.72, "int32": 0.52}[config.accumulator]
    guard_cost = {"full": 0.42, "boundary": 0.16, "none": 0.00}[config.guard]
    cache_cost = {"none": 0.28, "full": 0.34, "length": 0.04}[config.cache_key]
    chunk_cost = 0.44 / math.sqrt(float(config.chunk_size))
    cost = accumulator_cost + guard_cost + cache_cost + chunk_cost
    min_cost = 0.52 + 0.00 + 0.04 + 0.44 / 8.0
    max_cost = 1.00 + 0.42 + 0.34 + 0.44
    utility = 1.0 - (cost - min_cost) / (max_cost - min_cost)
    return max(0.0, min(1.0, utility))


def direct_cases(seed: str, count: int) -> list[Case]:
    """Fresh terminal cases from a frozen broad source population.

    The family is frozen in code, but the concrete cases are generated from a
    post-trajectory seed. It intentionally does not call RGG-001's external
    case generator or reuse any RGG-001 holdout data.
    """
    rng = random.Random(f"rgg002:progress:direct:{seed}")
    out: list[Case] = []
    repeated_lengths = (7, 11, 19, 31)
    for i in range(int(count)):
        mode = i % 5
        if mode == 0:  # broad mixed magnitude
            n = rng.randint(1, 128)
            xs = tuple(rng.randint(-(1 << 31), (1 << 31)) for _ in range(n))
        elif mode == 1:  # cancellation with a small residual
            pairs = rng.randint(2, 32)
            vals = [rng.randint(-(1 << 30), (1 << 30)) for _ in range(pairs)]
            residual = rng.randint(-100_000, 100_000)
            xs = tuple(vals + [-v for v in vals] + [residual])
        elif mode == 2:  # repeated shape, distinct contents
            n = repeated_lengths[(i // 5) % len(repeated_lengths)]
            xs = tuple(rng.randint(-5_000_000, 5_000_000) for _ in range(n))
        elif mode == 3:  # mixed scales in one reduction
            n = rng.randint(8, 96)
            xs = tuple(
                rng.randint(-(1 << 30), (1 << 30)) if j % 3 == 0 else rng.randint(-50_000, 50_000)
                for j in range(n)
            )
        else:  # structured positive/negative blocks
            n = rng.randint(12, 72)
            base = rng.randint(1 << 26, 1 << 30)
            xs = tuple((base if j < n // 2 else -base) + rng.randint(-1000, 1000) for j in range(n))
        out.append(Case(xs))
    return out


def direct_correctness(config: Config, cases: list[Case]) -> float:
    p = CandidateProgram(config)
    passed = 0
    for case in cases:
        passed += int(p(case.values) == case.expected)
    return passed / len(cases) if cases else 1.0


def relational_correctness(config: Config, seed: str, checks: int) -> float:
    rng = random.Random(f"rgg002:progress:relations:{seed}")
    passed = 0
    total = 0
    for _ in range(int(checks)):
        n = rng.randint(3, 48)
        xs = tuple(rng.randint(-(1 << 29), (1 << 29)) for _ in range(n))

        # Permutation invariance.
        perm = list(xs)
        rng.shuffle(perm)
        p = CandidateProgram(config)
        passed += int(p(xs) == sum(xs) and p(tuple(perm)) == sum(xs))
        total += 1

        # Sign symmetry.
        p = CandidateProgram(config)
        a = p(xs)
        b = p(tuple(-v for v in xs))
        passed += int(a == sum(xs) and b == -sum(xs))
        total += 1

        # Partition additivity, evaluated with independent program instances.
        cut = rng.randint(1, n - 1)
        whole = CandidateProgram(config)(xs)
        left = CandidateProgram(config)(xs[:cut])
        right = CandidateProgram(config)(xs[cut:])
        passed += int(whole == left + right == sum(xs))
        total += 1

        # Extensionality on same-length distinct inputs. This is a general
        # function property, not a reused RGG-001 holdout case.
        ys = tuple(rng.randint(-(1 << 29), (1 << 29)) for _ in range(n))
        p = CandidateProgram(config)
        ax = p(xs)
        ay = p(ys)
        passed += int(ax == sum(xs) and ay == sum(ys))
        total += 1
    return passed / total if total else 1.0


def config_progress_score(config: Config, *, direct: list[Case], relation_seed: str, relation_checks: int) -> dict[str, float]:
    d = direct_correctness(config, direct)
    r = relational_correctness(config, relation_seed, relation_checks)
    semantic = 0.60 * d + 0.40 * r
    speed = speed_utility(config)
    # Speed is useful only to the extent semantics hold. This prevents a fast,
    # wrong implementation from manufacturing "progress" through proxy speed.
    quality = semantic * (0.90 + 0.10 * speed)
    return {"direct": d, "relational": r, "semantic": semantic, "speed": speed, "quality": quality}


def _state_weights(state: dict) -> Iterable[tuple[Config, float]]:
    for a, g, c, h in product(ACCUMULATORS, GUARDS, CACHE_KEYS, CHUNK_SIZES):
        w = (
            float(state["accumulator"].get(a, 0.0))
            * float(state["guard"].get(g, 0.0))
            * float(state["cache_key"].get(c, 0.0))
            * float(state["chunk_size"].get(str(h), state["chunk_size"].get(h, 0.0)))
        )
        if w:
            yield Config(a, g, c, h), w


def generator_progress(state: dict, *, seed: str, direct_case_count: int, relation_checks: int) -> dict[str, float]:
    cases = direct_cases(f"{seed}:direct", direct_case_count)
    totals = {"direct": 0.0, "relational": 0.0, "semantic": 0.0, "speed": 0.0, "quality": 0.0}
    mass = 0.0
    for config, weight in _state_weights(state):
        s = config_progress_score(
            config,
            direct=cases,
            relation_seed=f"{seed}:relations:{config.accumulator}:{config.guard}:{config.cache_key}:{config.chunk_size}",
            relation_checks=relation_checks,
        )
        mass += weight
        for key in totals:
            totals[key] += weight * s[key]
    if not (0.999999 <= mass <= 1.000001):
        raise ValueError(f"generator probability mass must equal 1, got {mass}")
    return totals


def initial_state() -> dict:
    return {
        "accumulator": {"python": 0.62, "int64": 0.28, "int32": 0.10},
        "guard": {"full": 0.62, "boundary": 0.28, "none": 0.10},
        "cache_key": {"none": 0.52, "full": 0.38, "length": 0.10},
        "chunk_size": {"1": 0.20, "4": 0.30, "16": 0.30, "64": 0.20},
        "revision": 0,
    }


def point_state(accumulator: str, guard: str, cache_key: str, chunk_size: int) -> dict:
    return {
        "accumulator": {k: float(k == accumulator) for k in ACCUMULATORS},
        "guard": {k: float(k == guard) for k in GUARDS},
        "cache_key": {k: float(k == cache_key) for k in CACHE_KEYS},
        "chunk_size": {str(k): float(k == chunk_size) for k in CHUNK_SIZES},
        "revision": 0,
    }


def calibration(*, direct_case_count: int = 192, relation_checks: int = 32, repeats: int = 32) -> dict:
    risky = point_state("int32", "none", "length", 64)
    safe_slow = point_state("python", "full", "full", 1)
    safe_fast = point_state("int64", "full", "full", 64)
    risky_q = generator_progress(risky, seed="CAL:RISKY", direct_case_count=direct_case_count, relation_checks=relation_checks)["quality"]
    slow_q = generator_progress(safe_slow, seed="CAL:SAFE", direct_case_count=direct_case_count, relation_checks=relation_checks)["quality"]
    fast_q = generator_progress(safe_fast, seed="CAL:SAFE", direct_case_count=direct_case_count, relation_checks=relation_checks)["quality"]
    initial_scores = [
        generator_progress(initial_state(), seed=f"CAL:NOISE:{i}", direct_case_count=direct_case_count, relation_checks=relation_checks)["quality"]
        for i in range(int(repeats))
    ]
    return {
        "schema": "openline.ace.rgg002.progress-calibration.v1",
        "standing": "PRE_PRIMARY_CALIBRATION_ONLY",
        "risky_quality": risky_q,
        "safe_slow_quality": slow_q,
        "safe_fast_quality": fast_q,
        "safe_fast_advantage": fast_q - slow_q,
        "initial_mean": mean(initial_scores),
        "initial_panel_sd": pstdev(initial_scores),
        "repeats": int(repeats),
        "passed": bool(slow_q >= risky_q + 0.20 and fast_q >= slow_q + 0.01),
        "primary_claim_evidence": False,
    }
