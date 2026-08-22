from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ClaimGraph:
    claims: frozenset[str]
    edges: tuple[tuple[str, str], ...]

    @classmethod
    def from_mapping(cls, value: dict[str, object]) -> "ClaimGraph":
        claims = frozenset(str(item) for item in value["claims"])
        edges = tuple((str(edge[0]), str(edge[1])) for edge in value["edges"])
        return cls(claims=claims, edges=edges)


@dataclass(frozen=True)
class Prediction:
    reopened: frozenset[str]
    retained: frozenset[str]

    @classmethod
    def build(cls, *, claims: Iterable[str], reopened: Iterable[str]) -> "Prediction":
        claim_set = frozenset(claims)
        reopened_set = frozenset(reopened)
        unknown = reopened_set - claim_set
        if unknown:
            raise ValueError(f"unknown reopened claims: {sorted(unknown)}")
        return cls(reopened=reopened_set, retained=claim_set - reopened_set)
