from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from .model import ArmResult, Candidate, Grade

class SubstrateAdapter(Protocol):
    substrate_id: str
    substrate_class: str
    def candidates(self) -> tuple[Candidate, ...]: ...
    def baseline(self, candidate: Candidate) -> ArmResult: ...
    def active(self, candidate: Candidate) -> ArmResult: ...
    def sham(self, candidate: Candidate) -> ArmResult: ...
    def restoration(self, candidate: Candidate) -> ArmResult: ...

def grade_candidate(candidate: Candidate, *, baseline: ArmResult, active: ArmResult, sham: ArmResult, restoration: ArmResult) -> Grade:
    matched = active.nuisance == sham.nuisance
    common = dict(
        candidate_id=candidate.candidate_id,
        baseline_success=baseline.outcome.success,
        active_success=active.outcome.success,
        sham_success=sham.outcome.success,
        restoration_success=restoration.outcome.success,
        nuisance_matched=matched,
    )
    if not matched:
        return Grade("UNDECIDABLE", "SHAM_NOT_MATCHED", **common)
    if not baseline.outcome.success:
        return Grade("UNDECIDABLE", "BASELINE_NOT_HEALTHY", **common)
    if not active.outcome.success and sham.outcome.success and restoration.outcome.success:
        return Grade("SUPPORTED", "ACTIVE_BREAK_SHAM_SURVIVES_RESTORATION_RECOVERS", **common)
    if active.outcome.success and sham.outcome.success and restoration.outcome.success:
        return Grade("REJECTED_RITUAL", "TARGETED_BREAK_HAS_NO_BEHAVIORAL_EFFECT", **common)
    return Grade("UNDECIDABLE", "NON_DISCRIMINATING_OUTCOME_PATTERN", **common)

@dataclass(frozen=True)
class AuditRecord:
    substrate_id: str
    substrate_class: str
    candidate: Candidate
    baseline: ArmResult
    active: ArmResult
    sham: ArmResult
    restoration: ArmResult
    grade: Grade

    def to_dict(self) -> dict[str, object]:
        def arm(value: ArmResult) -> dict[str, object]:
            return {
                "arm": value.arm,
                "success": value.outcome.success,
                "oracle": value.outcome.oracle,
                "details": dict(value.outcome.details),
                "nuisance": {
                    "mutated_fields": value.nuisance.mutated_fields,
                    "delayed_ticks": value.nuisance.delayed_ticks,
                    "payload_units": value.nuisance.payload_units,
                },
            }
        return {
            "substrate_id": self.substrate_id,
            "substrate_class": self.substrate_class,
            "candidate": {
                "candidate_id": self.candidate.candidate_id,
                "text": self.candidate.text,
                "family": self.candidate.family,
            },
            "baseline": arm(self.baseline),
            "active": arm(self.active),
            "sham": arm(self.sham),
            "restoration": arm(self.restoration),
            "grade": self.grade.to_dict(),
        }

def audit_adapter(adapter: SubstrateAdapter) -> tuple[AuditRecord, ...]:
    out = []
    for candidate in adapter.candidates():
        baseline = adapter.baseline(candidate)
        active = adapter.active(candidate)
        sham = adapter.sham(candidate)
        restoration = adapter.restoration(candidate)
        out.append(AuditRecord(
            adapter.substrate_id,
            adapter.substrate_class,
            candidate,
            baseline,
            active,
            sham,
            restoration,
            grade_candidate(candidate, baseline=baseline, active=active, sham=sham, restoration=restoration),
        ))
    return tuple(out)
