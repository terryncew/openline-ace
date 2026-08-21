"""Closed data model for the held-out EnvHarness mechanism tournament."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


CLAUSE_ID = "fresh-test-evidence-bound-to-current-patch"


class Standing(str, Enum):
    SUPPORTED_NATIVE = "SUPPORTED_NATIVE"
    REJECTED_IMPOSED = "REJECTED_IMPOSED"
    REJECTED_NUISANCE = "REJECTED_NUISANCE"
    INVALID = "INVALID"


class Split(str, Enum):
    DEVELOPMENT = "development"
    EVALUATION = "evaluation"


@dataclass(frozen=True)
class Energy:
    hook_calls: int
    field_mutations: int
    payload_bucket: int
    synthetic_delay: int

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Energy":
        return cls(
            hook_calls=int(value["hook_calls"]),
            field_mutations=int(value["field_mutations"]),
            payload_bucket=int(value["payload_bucket"]),
            synthetic_delay=int(value["synthetic_delay"]),
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "field_mutations": self.field_mutations,
            "hook_calls": self.hook_calls,
            "payload_bucket": self.payload_bucket,
            "synthetic_delay": self.synthetic_delay,
        }


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    split: Split
    layers: tuple[str, ...]
    candidate_clause: str
    active_energy: Energy
    sham_energy: Energy
    proposal_digest: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Proposal":
        return cls(
            proposal_id=str(value["proposal_id"]),
            split=Split(value["split"]),
            layers=tuple(str(item) for item in value["layers"]),
            candidate_clause=str(value["candidate_clause"]),
            active_energy=Energy.from_dict(value["active_energy"]),
            sham_energy=Energy.from_dict(value["sham_energy"]),
            proposal_digest=str(value["proposal_digest"]),
        )

    def public_view(self) -> dict[str, Any]:
        """What either discovery policy may observe before intervention."""
        return {
            "candidate_clause": self.candidate_clause,
            "proposal_digest": self.proposal_digest,
        }


@dataclass(frozen=True)
class Task:
    task_id: str
    correct_patch: str
    alternate_patch: str
    nuisance_seed: int

    def patch_hash(self, patch: str) -> str:
        from .canonical import canonical_digest

        return canonical_digest({"patch": patch, "task_id": self.task_id})


@dataclass(frozen=True)
class EpisodeOutcome:
    arm: str
    external_success: bool
    artifact_valid: bool
    submitted: bool
    action_count: int
    recovery_horizon: int | None
    trace_digest: str
    energy: Energy

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_count": self.action_count,
            "arm": self.arm,
            "artifact_valid": self.artifact_valid,
            "energy": self.energy.to_dict(),
            "external_success": self.external_success,
            "recovery_horizon": self.recovery_horizon,
            "submitted": self.submitted,
            "trace_digest": self.trace_digest,
        }


@dataclass(frozen=True)
class QueryTranscript:
    active: EpisodeOutcome
    sham: EpisodeOutcome
    restoration: EpisodeOutcome
    query_count: int = 3

    def signature(self) -> tuple[bool, bool, bool, bool, int]:
        return (
            self.active.external_success,
            self.active.artifact_valid,
            self.sham.external_success,
            self.restoration.external_success,
            int(self.restoration.recovery_horizon or 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active.to_dict(),
            "query_count": self.query_count,
            "restoration": self.restoration.to_dict(),
            "sham": self.sham.to_dict(),
        }


@dataclass(frozen=True)
class PolicyDecision:
    standing: Standing
    predicted_recovery_horizon: int
    explanation_code: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "explanation_code": self.explanation_code,
            "predicted_recovery_horizon": self.predicted_recovery_horizon,
            "standing": self.standing.value,
        }

