from __future__ import annotations

from dataclasses import replace

from .baseline import mint_baseline, mint_successor_baseline
from .model import ClaimDependency, DimensionSpec, StateSnapshot, VerifiedBaseline
from .observer import DriftObserver


DOMAIN_SPECS = (
    DimensionSpec(name="readme_hash", kind="equality", epsilon_micros=0),
    DimensionSpec(name="code_hash", kind="equality", epsilon_micros=0),
    DimensionSpec(
        name="sensor_bias_micros",
        kind="numeric",
        epsilon_micros=200_000,
        scale=100_000,
    ),
)

CLAIMS = (
    ClaimDependency(
        claim_id="merge-current-patch",
        explicit_dimensions=(
            "policy_hash",
            "action_binding",
            "evidence_bundle_hash",
            "evidence_epoch",
            "witness_id",
            "witness_version",
            "code_hash",
            "reference_receipt",
        ),
    ),
    ClaimDependency(
        claim_id="docs-reviewed",
        explicit_dimensions=("readme_hash",),
    ),
    ClaimDependency(
        claim_id="control-stable",
        explicit_dimensions=("sensor_bias_micros",),
    ),
    ClaimDependency(
        claim_id="telemetry-safe",
        candidate_dimensions=("sensor_bias_micros",),
    ),
)


def baseline() -> VerifiedBaseline:
    return mint_baseline(
        verified_at="2026-08-21T18:00:00Z",
        max_age_seconds=3600,
        control_plane={
            "policy_hash": "policy-v1",
            "action_binding": "commit-A",
            "evidence_bundle_hash": "evidence-A",
            "evidence_epoch": 7,
            "witness_id": "verifier",
            "witness_version": 3,
        },
        domain={
            "readme_hash": "docs-A",
            "code_hash": "code-A",
            "sensor_bias_micros": 10_000,
        },
    )


def current(reference: VerifiedBaseline) -> StateSnapshot:
    return StateSnapshot(
        reference_receipt_id=reference.receipt_id,
        observed_at="2026-08-21T18:10:00Z",
        control_plane=dict(reference.control_plane),
        domain=dict(reference.domain),
    )


def run_fixture() -> dict[str, object]:
    observer = DriftObserver(DOMAIN_SPECS)
    base = baseline()
    seed = current(base)

    readme = replace(
        seed,
        domain={**seed.domain, "readme_hash": "docs-B"},
    )
    patch = replace(
        seed,
        control_plane={
            **seed.control_plane,
            "action_binding": "commit-B",
            "evidence_bundle_hash": "evidence-B",
            "evidence_epoch": 8,
        },
        domain={**seed.domain, "code_hash": "code-B"},
    )
    sensor_small = replace(
        seed,
        domain={**seed.domain, "sensor_bias_micros": 15_000},
    )
    sensor_large = replace(
        seed,
        domain={**seed.domain, "sensor_bias_micros": 250_000},
    )
    witness = replace(
        seed,
        control_plane={**seed.control_plane, "witness_version": 4},
    )

    scenarios = {
        "unchanged": observer.observe(
            baseline=base, current=seed, claims=CLAIMS
        ),
        "readme_only": observer.observe(
            baseline=base, current=readme, claims=CLAIMS
        ),
        "patch_rebind": observer.observe(
            baseline=base, current=patch, claims=CLAIMS
        ),
        "sensor_small": observer.observe(
            baseline=base, current=sensor_small, claims=CLAIMS
        ),
        "sensor_large": observer.observe(
            baseline=base, current=sensor_large, claims=CLAIMS
        ),
        "witness_upgrade": observer.observe(
            baseline=base, current=witness, claims=CLAIMS
        ),
        "baseline_expired": observer.observe(
            baseline=base,
            current=seed,
            claims=CLAIMS,
            now="2026-08-21T20:00:01Z",
        ),
    }

    revoked = replace(base, support_standing="REVOKED")
    scenarios["baseline_revoked"] = observer.observe(
        baseline=revoked,
        current=seed,
        claims=CLAIMS,
    )

    successor = mint_successor_baseline(
        previous=base,
        verified_state=patch,
        verified_at="2026-08-21T18:12:00Z",
    )

    return {
        "profile": "openline.drift-observer-001.fixture-result.v1",
        "base_commit": "04b814bf5140a4fcaee781efbb25d5db2320adfc",
        "status": "VERIFIED_CONTINUITY_CONFORMANCE_PASS",
        "delta_hol_definition": "dependency-aware verified-reference displacement",
        "mandatory_control_dimensions": [
            "reference_receipt",
            "policy_hash",
            "action_binding",
            "evidence_bundle_hash",
            "evidence_epoch",
            "witness_id",
            "witness_version",
        ],
        "display_scalar_authoritative": False,
        "policy_authority": "NONE",
        "runtime_permission": "NONE",
        "baseline": {
            "receipt_id": base.receipt_id,
            "verified_at": base.verified_at,
            "max_age_seconds": base.max_age_seconds,
        },
        "successor_baseline": {
            "receipt_id": successor.receipt_id,
            "parent_receipt_id": successor.parent_receipt_id,
            "verified_at": successor.verified_at,
        },
        "scenarios": {
            name: observation.to_dict()
            for name, observation in scenarios.items()
        },
    }
