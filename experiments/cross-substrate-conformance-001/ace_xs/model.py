from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

@dataclass(frozen=True)
class Nuisance:
    mutated_fields: int
    delayed_ticks: int
    payload_units: int

@dataclass(frozen=True)
class Outcome:
    success: bool
    oracle: str
    details: Mapping[str, object]

@dataclass(frozen=True)
class ArmResult:
    arm: str
    outcome: Outcome
    nuisance: Nuisance

@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    text: str
    family: str

@dataclass(frozen=True)
class Grade:
    standing: str
    reason: str
    candidate_id: str
    baseline_success: bool
    active_success: bool
    sham_success: bool
    restoration_success: bool
    nuisance_matched: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "standing": self.standing,
            "reason": self.reason,
            "candidate_id": self.candidate_id,
            "baseline_success": self.baseline_success,
            "active_success": self.active_success,
            "sham_success": self.sham_success,
            "restoration_success": self.restoration_success,
            "nuisance_matched": self.nuisance_matched,
        }
