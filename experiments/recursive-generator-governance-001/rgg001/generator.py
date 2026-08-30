from __future__ import annotations

import random
from typing import Any

from .model import CandidateConfig, GeneratorState


def initial_generator() -> GeneratorState:
    # Safe-biased but non-degenerate. There is genuine room to improve speed
    # without making "freeze everything" the only coherent strategy.
    return GeneratorState(
        accumulator={"python": 0.62, "int64": 0.28, "int32": 0.10},
        guard={"full": 0.62, "boundary": 0.28, "none": 0.10},
        cache_key={"none": 0.52, "full": 0.38, "length": 0.10},
        chunk_size={1: 0.20, 4: 0.30, 16: 0.30, 64: 0.20},
        revision=0,
    )


def _choice(rng: random.Random, weights: dict[Any, float]):
    items = list(weights.keys())
    total = sum(float(weights[k]) for k in items)
    cursor = rng.random() * total
    cumulative = 0.0
    for item in items:
        cumulative += float(weights[item])
        if cursor <= cumulative:
            return item
    return items[-1]


def sample_candidate(state: GeneratorState, rng: random.Random) -> CandidateConfig:
    return CandidateConfig(
        accumulator=str(_choice(rng, state.accumulator)),
        guard=str(_choice(rng, state.guard)),
        cache_key=str(_choice(rng, state.cache_key)),
        chunk_size=int(_choice(rng, state.chunk_size)),
    )


def sample_pool(state: GeneratorState, *, seed: int | str, count: int) -> list[CandidateConfig]:
    rng = random.Random(str(seed))
    return [sample_candidate(state, rng) for _ in range(int(count))]


def _shift(weights: dict, target, step: float) -> dict:
    if target not in weights:
        raise KeyError(target)
    step = max(0.0, min(0.95, float(step)))
    out = {k: float(v) * (1.0 - step) for k, v in weights.items()}
    out[target] += step
    total = sum(out.values())
    return {k: v / total for k, v in out.items()}


def propose_dimension_update(
    state: GeneratorState,
    *,
    winner: CandidateConfig,
    dimension: str,
    step: float,
) -> GeneratorState:
    out = state.clone()
    if dimension == "accumulator":
        out.accumulator = _shift(out.accumulator, winner.accumulator, step)
    elif dimension == "guard":
        out.guard = _shift(out.guard, winner.guard, step)
    elif dimension == "cache_key":
        out.cache_key = _shift(out.cache_key, winner.cache_key, step)
    elif dimension == "chunk_size":
        out.chunk_size = _shift(out.chunk_size, winner.chunk_size, step)
    else:
        raise ValueError(dimension)
    out.revision += 1
    return out


def proposal_signature(config: CandidateConfig) -> str:
    return f"{config.accumulator}|{config.guard}|{config.cache_key}|{config.chunk_size}"
