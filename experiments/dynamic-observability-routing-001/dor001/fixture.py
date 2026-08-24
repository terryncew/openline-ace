from __future__ import annotations

from dataclasses import dataclass
from .core import ChannelManifest, ChannelSpec, EvidenceReceipt


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    partition: str
    mechanism_id: str
    true_state: str
    prior_receipts: tuple[EvidenceReceipt, ...]
    reveal_times: dict[str, int]
    nuisance_positive_times: dict[str, int]
    oracle_diagnostic_channels: tuple[str, ...]
    horizon: int = 7

    def value_at(self, channel_id: str, t: int) -> float:
        nuisance_t = self.nuisance_positive_times.get(channel_id)
        if nuisance_t is not None and t >= nuisance_t:
            return 1.0
        if self.true_state == "transition":
            reveal_t = self.reveal_times.get(channel_id)
            if reveal_t is not None and t >= reveal_t:
                return 1.0
        return 0.0


def frozen_manifest() -> ChannelManifest:
    return ChannelManifest(
        budget_per_tick=2,
        sentinel_required=True,
        channels=(
            ChannelSpec("sentinel", 1, 0, "receiver_sentinel", "binary_transition_indicator", mandatory_sentinel=True, can_resolve=True),
            ChannelSpec("headline", 1, 1, "headline_monitor", "binary_transition_indicator", can_resolve=True),
            ChannelSpec("diag_alpha", 1, 1, "diagnostic_bus_alpha", "binary_transition_indicator", routing_tags=("alpha",), can_resolve=True),
            ChannelSpec("diag_beta", 1, 1, "diagnostic_bus_beta", "binary_transition_indicator", routing_tags=("beta",), can_resolve=True),
            ChannelSpec("diag_gamma", 1, 1, "diagnostic_bus_gamma", "binary_transition_indicator", routing_tags=("gamma",), can_resolve=True),
            ChannelSpec("diag_delta", 1, 1, "diagnostic_bus_delta", "binary_transition_indicator", routing_tags=("delta",), can_resolve=True),
        ),
    )


def _receipt(case: str, tag: str) -> EvidenceReceipt:
    return EvidenceReceipt(
        receipt_id=f"receipt:{case}:{tag}",
        issued_at=0,
        routing_tags=(tag,),
        provenance="verified_prior_fixture",
    )


def frozen_scenarios() -> tuple[Scenario, ...]:
    # Calibration scenarios exist only to validate the harness. Promotion metrics
    # are computed on the held-out partition below. The router never receives
    # partition, mechanism_id, reveal_times, nuisance timings, or oracle channels.
    return (
        Scenario(
            "cal-alpha", "calibration", "cal-mech-a", "transition",
            (_receipt("cal-alpha", "alpha"),),
            {"diag_alpha": 2, "sentinel": 5, "headline": 6}, {}, ("diag_alpha", "sentinel", "headline")
        ),
        Scenario(
            "cal-beta", "calibration", "cal-mech-b", "transition",
            (_receipt("cal-beta", "beta"),),
            {"diag_beta": 2, "sentinel": 5, "headline": 6}, {}, ("diag_beta", "sentinel", "headline")
        ),
        Scenario(
            "cal-headline-only", "calibration", "cal-mech-c", "transition",
            (_receipt("cal-headline-only", "alpha"),),
            {"sentinel": 4, "headline": 4}, {}, ("sentinel", "headline")
        ),
        Scenario(
            "cal-stable-nuisance", "calibration", "cal-mech-d", "stable",
            (_receipt("cal-stable-nuisance", "alpha"),),
            {}, {"diag_alpha": 1}, (), horizon=5
        ),

        # Held-out transition mechanisms: intentionally include helpful priors,
        # wrong priors, no precursor, nuisance positives, and an unmonitored
        # precursor so DOR can win, tie, or lose without changing the harness.
        Scenario(
            "ho-alpha-fast", "heldout", "heldout-mech-1", "transition",
            (_receipt("ho-alpha-fast", "alpha"),),
            {"diag_alpha": 1, "sentinel": 5, "headline": 6}, {}, ("diag_alpha", "sentinel", "headline")
        ),
        Scenario(
            "ho-beta-fast", "heldout", "heldout-mech-2", "transition",
            (_receipt("ho-beta-fast", "beta"),),
            {"diag_beta": 2, "sentinel": 5, "headline": 6}, {}, ("diag_beta", "sentinel", "headline")
        ),
        Scenario(
            "ho-gamma-fast", "heldout", "heldout-mech-3", "transition",
            (_receipt("ho-gamma-fast", "gamma"),),
            {"diag_gamma": 2, "sentinel": 5, "headline": 6}, {}, ("diag_gamma", "sentinel", "headline")
        ),
        Scenario(
            "ho-delta-fast", "heldout", "heldout-mech-4", "transition",
            (_receipt("ho-delta-fast", "delta"),),
            {"diag_delta": 3, "sentinel": 5, "headline": 6}, {}, ("diag_delta", "sentinel", "headline")
        ),
        Scenario(
            "ho-misprime-alpha-beta", "heldout", "heldout-mech-5", "transition",
            (_receipt("ho-misprime-alpha-beta", "alpha"),),
            {"diag_beta": 1, "sentinel": 5, "headline": 6}, {}, ("diag_beta", "sentinel", "headline")
        ),
        Scenario(
            "ho-no-precursor", "heldout", "heldout-mech-6", "transition",
            (_receipt("ho-no-precursor", "gamma"),),
            {"sentinel": 4, "headline": 4}, {}, ("sentinel", "headline")
        ),
        Scenario(
            "ho-unmonitored-precursor", "heldout", "heldout-mech-7", "transition",
            (_receipt("ho-unmonitored-precursor", "beta"),),
            {"sentinel": 4, "headline": 6}, {}, ("sentinel", "headline")
        ),
        Scenario(
            "ho-nuisance-alpha", "heldout", "heldout-mech-8", "transition",
            (_receipt("ho-nuisance-alpha", "alpha"),),
            {"sentinel": 5, "headline": 6}, {"diag_alpha": 1}, ("sentinel", "headline")
        ),
    )
