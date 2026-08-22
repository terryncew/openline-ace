from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CoverageResult:
    status: str
    explicit_dependents: tuple[str, ...]
    rejected_heuristics: tuple[str, ...]


def audit_mimic_excerpt(value: dict[str, Any]) -> CoverageResult:
    """Require an explicit downstream reference to the changed lab event.

    Patient/encounter equality, timing, and medication names are deliberately
    excluded from authority-bearing dependency evidence.
    """
    lab = value["selected_lab"]
    lab_id = str(lab["labevent_id"])
    schema = set(value["emar_schema"])
    dependents: list[str] = []

    for admin in value["same_hospitalization_medication_administrations"]:
        for key, raw in admin.items():
            if key in {"subject_id", "hadm_id", "charttime", "medication"}:
                continue
            if str(raw) == lab_id:
                dependents.append(str(admin["emar_id"]))

    has_reference_field = bool(
        {"labevent_id", "reason_reference", "reasonReference", "observation_id"} & schema
    )
    status = (
        "EXPLICIT_DEPENDENCY_AVAILABLE"
        if dependents or has_reference_field
        else "DEPENDENCY_COVERAGE_INSUFFICIENT"
    )
    return CoverageResult(
        status=status,
        explicit_dependents=tuple(sorted(set(dependents))),
        rejected_heuristics=("same_hospitalization", "temporal_proximity", "name_similarity"),
    )


def audit_fhir_control(value: dict[str, Any]) -> CoverageResult:
    changed = value["changed"]
    dependents: list[str] = []
    for resource in value["resources"]:
        if resource.get("resourceType") != "MedicationRequest":
            continue
        refs = resource.get("reasonReference", [])
        if any(ref.get("reference") == changed for ref in refs):
            dependents.append(resource["id"])
    status = "SELECTIVE_REOPENING_CAPABILITY_PASS" if dependents else "CONTROL_FAIL"
    return CoverageResult(
        status=status,
        explicit_dependents=tuple(sorted(dependents)),
        rejected_heuristics=(),
    )
