from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping


MANDATORY_CONTROL_DIMENSIONS = (
    "policy_hash",
    "action_binding",
    "evidence_bundle_hash",
    "evidence_epoch",
    "witness_id",
    "witness_version",
)


def parse_time(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamp_timezone_missing")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class DimensionSpec:
    name: str
    kind: str
    epsilon_micros: int
    scale: int = 1

    def __post_init__(self) -> None:
        if self.kind not in {"equality", "numeric"}:
            raise ValueError("dimension_kind_invalid")
        if not 0 <= self.epsilon_micros <= 1_000_000:
            raise ValueError("epsilon_out_of_range")
        if self.scale <= 0:
            raise ValueError("scale_must_be_positive")


@dataclass(frozen=True)
class VerifiedBaseline:
    receipt_id: str
    parent_receipt_id: str | None
    verified_at: str
    max_age_seconds: int
    support_standing: str
    control_plane: Mapping[str, object]
    domain: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.max_age_seconds <= 0:
            raise ValueError("max_age_seconds_must_be_positive")
        if self.support_standing not in {"STANDING", "REVOKED"}:
            raise ValueError("support_standing_invalid")
        missing = set(MANDATORY_CONTROL_DIMENSIONS) - set(self.control_plane)
        if missing:
            raise ValueError(
                "baseline_missing_control_dimensions:" + ",".join(sorted(missing))
            )


@dataclass(frozen=True)
class StateSnapshot:
    reference_receipt_id: str
    observed_at: str
    control_plane: Mapping[str, object]
    domain: Mapping[str, object]


@dataclass(frozen=True)
class ClaimDependency:
    claim_id: str
    explicit_dimensions: tuple[str, ...] = ()
    candidate_dimensions: tuple[str, ...] = ()


@dataclass(frozen=True)
class DistanceComponent:
    name: str
    plane: str
    distance_micros: int
    epsilon_micros: int
    crossed: bool
    saturated: bool
    missing: bool
    reference_value: object
    current_value: object

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "plane": self.plane,
            "distance_micros": self.distance_micros,
            "epsilon_micros": self.epsilon_micros,
            "crossed": self.crossed,
            "saturated": self.saturated,
            "missing": self.missing,
            "reference_value": self.reference_value,
            "current_value": self.current_value,
        }


@dataclass(frozen=True)
class ClaimImpact:
    claim_id: str
    disposition: str
    dimensions: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "claim_id": self.claim_id,
            "disposition": self.disposition,
            "dimensions": list(self.dimensions),
            "reason": self.reason,
        }
