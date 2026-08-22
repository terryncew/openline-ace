from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .model import (
    MANDATORY_CONTROL_DIMENSIONS,
    ClaimDependency,
    ClaimImpact,
    DimensionSpec,
    DistanceComponent,
    StateSnapshot,
    VerifiedBaseline,
    parse_time,
)


CONTROL_SPECS = {
    name: DimensionSpec(
        name=name,
        kind="equality",
        epsilon_micros=0,
        scale=1,
    )
    for name in MANDATORY_CONTROL_DIMENSIONS
}


@dataclass(frozen=True)
class Observation:
    status: str
    delta_hol: tuple[DistanceComponent, ...]
    crossed_dimensions: tuple[str, ...]
    saturated_dimensions: tuple[str, ...]
    claim_impacts: tuple[ClaimImpact, ...]
    display_scalar_micros: int
    display_scalar_authoritative: bool
    baseline_receipt_id: str
    policy_authority: str
    runtime_permission: str

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "delta_hol": [component.to_dict() for component in self.delta_hol],
            "crossed_dimensions": list(self.crossed_dimensions),
            "saturated_dimensions": list(self.saturated_dimensions),
            "claim_impacts": [impact.to_dict() for impact in self.claim_impacts],
            "display_scalar": {
                "value_micros": self.display_scalar_micros,
                "authoritative": self.display_scalar_authoritative,
                "aggregation": "max_component_for_display_only",
            },
            "baseline_receipt_id": self.baseline_receipt_id,
            "policy_authority": self.policy_authority,
            "runtime_permission": self.runtime_permission,
        }


class DriftObserver:
    """Non-authoritative verified-reference displacement observer."""

    def __init__(self, domain_specs: Iterable[DimensionSpec]) -> None:
        domain = tuple(domain_specs)
        names = [spec.name for spec in domain]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(
                "duplicate_domain_dimensions:" + ",".join(duplicates)
            )
        forbidden = sorted(set(names) & set(MANDATORY_CONTROL_DIMENSIONS))
        if forbidden:
            raise ValueError(
                "mandatory_control_dimension_override:" + ",".join(forbidden)
            )
        self._domain_specs = {spec.name: spec for spec in domain}

    @staticmethod
    def _component(
        *,
        spec: DimensionSpec,
        plane: str,
        reference: Mapping[str, object],
        current: Mapping[str, object],
    ) -> DistanceComponent:
        ref_present = spec.name in reference
        cur_present = spec.name in current
        missing = not ref_present or not cur_present
        ref_value = reference.get(spec.name)
        cur_value = current.get(spec.name)

        if missing:
            distance = 1_000_000
            saturated = False
        elif spec.kind == "equality":
            distance = (
                0
                if type(ref_value) is type(cur_value) and ref_value == cur_value
                else 1_000_000
            )
            saturated = False
        else:
            if isinstance(ref_value, bool) or isinstance(cur_value, bool):
                raise ValueError(f"numeric_dimension_boolean:{spec.name}")
            if not isinstance(ref_value, (int, float)) or not isinstance(
                cur_value, (int, float)
            ):
                raise ValueError(f"numeric_dimension_non_numeric:{spec.name}")
            raw = abs(float(cur_value) - float(ref_value)) / float(spec.scale)
            saturated = raw > 1.0
            distance = min(1_000_000, round(raw * 1_000_000))

        return DistanceComponent(
            name=spec.name,
            plane=plane,
            distance_micros=distance,
            epsilon_micros=spec.epsilon_micros,
            crossed=distance > spec.epsilon_micros,
            saturated=saturated,
            missing=missing,
            reference_value=ref_value,
            current_value=cur_value,
        )

    @staticmethod
    def _baseline_reason(
        baseline: VerifiedBaseline,
        now: str,
    ) -> str | None:
        if baseline.support_standing != "STANDING":
            return "BASELINE_SUPPORT_REVOKED"
        age = int(
            (
                parse_time(now) - parse_time(baseline.verified_at)
            ).total_seconds()
        )
        if age < 0:
            return "BASELINE_FROM_FUTURE"
        if age > baseline.max_age_seconds:
            return "BASELINE_EXPIRED"
        return None

    @staticmethod
    def _baseline_invalid_impacts(
        claims: Iterable[ClaimDependency],
        reason: str,
    ) -> tuple[ClaimImpact, ...]:
        return tuple(
            ClaimImpact(
                claim_id=claim.claim_id,
                disposition="REOPEN",
                dimensions=("baseline_receipt",),
                reason=reason,
            )
            for claim in claims
        )

    @staticmethod
    def _impacts(
        claims: Iterable[ClaimDependency],
        crossed: set[str],
    ) -> tuple[ClaimImpact, ...]:
        impacts: list[ClaimImpact] = []
        for claim in claims:
            explicit = tuple(
                sorted(crossed.intersection(claim.explicit_dimensions))
            )
            candidates = tuple(
                sorted(crossed.intersection(claim.candidate_dimensions))
            )
            if explicit:
                impacts.append(
                    ClaimImpact(
                        claim_id=claim.claim_id,
                        disposition="REOPEN",
                        dimensions=explicit,
                        reason="EXPLICIT_DEPENDENCY_DISPLACED",
                    )
                )
            elif candidates:
                impacts.append(
                    ClaimImpact(
                        claim_id=claim.claim_id,
                        disposition="ACE_RECOMMENDED",
                        dimensions=candidates,
                        reason="CANDIDATE_DEPENDENCY_DISPLACED",
                    )
                )
            else:
                impacts.append(
                    ClaimImpact(
                        claim_id=claim.claim_id,
                        disposition="RETAIN",
                        dimensions=(),
                        reason="NO_DECLARED_DEPENDENCY_DISPLACED",
                    )
                )
        return tuple(impacts)

    def observe(
        self,
        *,
        baseline: VerifiedBaseline,
        current: StateSnapshot,
        claims: Iterable[ClaimDependency],
        now: str | None = None,
    ) -> Observation:
        claims = tuple(claims)
        effective_now = now or current.observed_at
        baseline_reason = self._baseline_reason(baseline, effective_now)

        if baseline_reason is not None:
            impacts = self._baseline_invalid_impacts(claims, baseline_reason)
            return Observation(
                status="BASELINE_REVERIFY_REQUIRED",
                delta_hol=(),
                crossed_dimensions=("baseline_receipt",),
                saturated_dimensions=(),
                claim_impacts=impacts,
                display_scalar_micros=1_000_000,
                display_scalar_authoritative=False,
                baseline_receipt_id=baseline.receipt_id,
                policy_authority="NONE",
                runtime_permission="NONE",
            )

        components: list[DistanceComponent] = []
        components.append(
            DistanceComponent(
                name="reference_receipt",
                plane="control",
                distance_micros=(
                    0 if current.reference_receipt_id == baseline.receipt_id else 1_000_000
                ),
                epsilon_micros=0,
                crossed=current.reference_receipt_id != baseline.receipt_id,
                saturated=False,
                missing=False,
                reference_value=baseline.receipt_id,
                current_value=current.reference_receipt_id,
            )
        )

        for spec in CONTROL_SPECS.values():
            components.append(
                self._component(
                    spec=spec,
                    plane="control",
                    reference=baseline.control_plane,
                    current=current.control_plane,
                )
            )
        for spec in self._domain_specs.values():
            components.append(
                self._component(
                    spec=spec,
                    plane="domain",
                    reference=baseline.domain,
                    current=current.domain,
                )
            )

        crossed = {component.name for component in components if component.crossed}
        impacts = self._impacts(claims, crossed)
        saturated = tuple(
            sorted(
                component.name
                for component in components
                if component.saturated
            )
        )
        display = max(
            (component.distance_micros for component in components),
            default=0,
        )

        return Observation(
            status=(
                "DISPLACEMENT_DETECTED"
                if crossed
                else "WITHIN_DECLARED_ENVELOPE"
            ),
            delta_hol=tuple(components),
            crossed_dimensions=tuple(sorted(crossed)),
            saturated_dimensions=saturated,
            claim_impacts=impacts,
            display_scalar_micros=display,
            display_scalar_authoritative=False,
            baseline_receipt_id=baseline.receipt_id,
            policy_authority="NONE",
            runtime_permission="NONE",
        )
