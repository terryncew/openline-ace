from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ACCUMULATORS = ("python", "int64", "int32")
GUARDS = ("full", "boundary", "none")
CACHE_KEYS = ("none", "full", "length")
CHUNK_SIZES = (1, 4, 16, 64)
DIMENSIONS = ("accumulator", "guard", "cache_key", "chunk_size")


@dataclass(frozen=True)
class CandidateConfig:
    accumulator: str
    guard: str
    cache_key: str
    chunk_size: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "accumulator": self.accumulator,
            "guard": self.guard,
            "cache_key": self.cache_key,
            "chunk_size": self.chunk_size,
        }


@dataclass
class GeneratorState:
    accumulator: dict[str, float]
    guard: dict[str, float]
    cache_key: dict[str, float]
    chunk_size: dict[int, float]
    revision: int = 0

    def clone(self) -> "GeneratorState":
        return GeneratorState(
            accumulator=dict(self.accumulator),
            guard=dict(self.guard),
            cache_key=dict(self.cache_key),
            chunk_size=dict(self.chunk_size),
            revision=self.revision,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "accumulator": dict(sorted(self.accumulator.items())),
            "guard": dict(sorted(self.guard.items())),
            "cache_key": dict(sorted(self.cache_key.items())),
            "chunk_size": {str(k): v for k, v in sorted(self.chunk_size.items())},
            "revision": self.revision,
        }


@dataclass(frozen=True)
class MutationProposal:
    proposal_id: str
    declared_tier: str
    targets: tuple[str, ...]
    persistent: bool
    shared: bool
    affects_future_proposals: bool
    constitutional: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Classification:
    effective_tier: str
    reason: str
    laundering_detected: bool


@dataclass(frozen=True)
class EvalScore:
    correctness: float
    speed: float
    score: float

    def as_dict(self) -> dict[str, float]:
        return {
            "correctness": self.correctness,
            "speed": self.speed,
            "score": self.score,
        }
