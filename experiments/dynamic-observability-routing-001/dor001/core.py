from __future__ import annotations

from dataclasses import dataclass, field, asdict
from hashlib import sha256
import json
from typing import Iterable


@dataclass(frozen=True)
class ChannelSpec:
    channel_id: str
    cost: int
    latency: int
    provenance: str
    resolution: str
    routing_tags: tuple[str, ...] = ()
    mandatory_sentinel: bool = False
    can_resolve: bool = True
    positive_threshold: float = 1.0


@dataclass(frozen=True)
class ChannelManifest:
    channels: tuple[ChannelSpec, ...]
    budget_per_tick: int
    sentinel_required: bool = True

    def by_id(self) -> dict[str, ChannelSpec]:
        return {c.channel_id: c for c in self.channels}

    def validate(self) -> None:
        ids = [c.channel_id for c in self.channels]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate channel_id")
        if self.budget_per_tick <= 0:
            raise ValueError("budget_per_tick must be positive")
        if any(c.cost <= 0 for c in self.channels):
            raise ValueError("channel costs must be positive")
        sentinels = [c for c in self.channels if c.mandatory_sentinel]
        if self.sentinel_required and not sentinels:
            raise ValueError("mandatory sentinel missing")
        if sum(c.cost for c in sentinels) > self.budget_per_tick:
            raise ValueError("sentinel cost exceeds budget")


@dataclass(frozen=True)
class Observation:
    t: int
    channel_id: str
    value: float


@dataclass(frozen=True)
class EvidenceReceipt:
    receipt_id: str
    issued_at: int
    routing_tags: tuple[str, ...]
    provenance: str = "verified_prior"


@dataclass(frozen=True)
class EvidenceState:
    as_of: int
    receipts: tuple[EvidenceReceipt, ...]
    observations: tuple[Observation, ...] = ()

    @property
    def routing_tags(self) -> tuple[str, ...]:
        tags: list[str] = []
        for receipt in self.receipts:
            if receipt.issued_at > self.as_of:
                raise ValueError("future receipt leaked into EvidenceState")
            tags.extend(receipt.routing_tags)
        return tuple(tags)

    def prior_observations(self, channel_id: str) -> tuple[Observation, ...]:
        return tuple(
            o for o in self.observations
            if o.channel_id == channel_id and o.t <= self.as_of
        )


@dataclass(frozen=True)
class MeasurementReceipt:
    schema: str
    scenario_id: str
    as_of: int
    evidence_receipt_ids: tuple[str, ...]
    selected_channels: tuple[str, ...]
    reason: dict[str, str]
    budget_limit: int
    budget_spent: int
    expires_at: int
    runtime_permission: str = "NONE"
    receipt_hash: str = field(default="")

    def with_hash(self) -> "MeasurementReceipt":
        payload = asdict(self)
        payload["receipt_hash"] = ""
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        digest = sha256(raw).hexdigest()
        return MeasurementReceipt(**{**payload, "receipt_hash": digest})


class Router:
    """Receipt-conditioned channel router.

    It never sees scenario truth, oracle rules, future receipts, or future observations.
    The only adaptive input is verified prior evidence plus measurements already observed.
    """

    def __init__(self, manifest: ChannelManifest):
        manifest.validate()
        self.manifest = manifest

    def _score(self, channel: ChannelSpec, evidence: EvidenceState) -> float:
        tags = set(evidence.routing_tags)
        tag_match = len(tags.intersection(channel.routing_tags))
        history = evidence.prior_observations(channel.channel_id)
        negative_samples = sum(1 for o in history if o.value < channel.positive_threshold)
        positive_samples = sum(1 for o in history if o.value >= channel.positive_threshold)

        # Frozen, deliberately simple rule: receipt match first; repeated clean samples
        # reduce urgency so the router explores. Headline remains the fallback.
        score = 4.0 * tag_match
        score += 1.0 if channel.channel_id == "headline" else 0.25
        score += 0.5 if not history else 0.0
        score -= 1.5 * negative_samples
        score += 2.0 * positive_samples
        score -= 0.05 * channel.latency
        return score

    def select(self, scenario_id: str, evidence: EvidenceState) -> MeasurementReceipt:
        available = self.manifest.by_id()
        selected: list[str] = []
        reasons: dict[str, str] = {}
        spent = 0

        sentinels = sorted(
            (c for c in self.manifest.channels if c.mandatory_sentinel),
            key=lambda c: c.channel_id,
        )
        for channel in sentinels:
            if spent + channel.cost > self.manifest.budget_per_tick:
                raise ValueError("mandatory sentinel does not fit budget")
            selected.append(channel.channel_id)
            spent += channel.cost
            reasons[channel.channel_id] = "mandatory_sentinel"

        candidates = [c for c in self.manifest.channels if not c.mandatory_sentinel]
        ranked = sorted(
            candidates,
            key=lambda c: (-self._score(c, evidence), c.cost, c.latency, c.channel_id),
        )
        for channel in ranked:
            if spent + channel.cost > self.manifest.budget_per_tick:
                continue
            selected.append(channel.channel_id)
            spent += channel.cost
            reasons[channel.channel_id] = (
                f"receipt_conditioned_score={self._score(channel, evidence):.3f}"
            )

        receipt = MeasurementReceipt(
            schema="openline.ace.dor001.measurement_receipt.v1",
            scenario_id=scenario_id,
            as_of=evidence.as_of,
            evidence_receipt_ids=tuple(r.receipt_id for r in evidence.receipts),
            selected_channels=tuple(selected),
            reason=reasons,
            budget_limit=self.manifest.budget_per_tick,
            budget_spent=spent,
            expires_at=evidence.as_of + 1,
            runtime_permission="NONE",
        )
        return receipt.with_hash()


class FixedHeadlinePolicy:
    def __init__(self, manifest: ChannelManifest):
        self.manifest = manifest
        self.manifest.validate()

    def select(self, scenario_id: str, evidence: EvidenceState) -> MeasurementReceipt:
        channels = self.manifest.by_id()
        required = [c for c in self.manifest.channels if c.mandatory_sentinel]
        headline = channels["headline"]
        chosen = required + [headline]
        spent = sum(c.cost for c in chosen)
        if spent > self.manifest.budget_per_tick:
            raise ValueError("fixed headline exceeds budget")
        return MeasurementReceipt(
            schema="openline.ace.dor001.measurement_receipt.v1",
            scenario_id=scenario_id,
            as_of=evidence.as_of,
            evidence_receipt_ids=tuple(r.receipt_id for r in evidence.receipts),
            selected_channels=tuple(c.channel_id for c in chosen),
            reason={c.channel_id: ("mandatory_sentinel" if c.mandatory_sentinel else "fixed_headline") for c in chosen},
            budget_limit=self.manifest.budget_per_tick,
            budget_spent=spent,
            expires_at=evidence.as_of + 1,
            runtime_permission="NONE",
        ).with_hash()


class EqualBudgetWidePolicy:
    """Mandatory sentinel plus deterministic round-robin coverage at the same budget."""

    def __init__(self, manifest: ChannelManifest):
        self.manifest = manifest
        self.manifest.validate()
        self._pool = tuple(
            sorted(c.channel_id for c in manifest.channels if not c.mandatory_sentinel)
        )

    def select(self, scenario_id: str, evidence: EvidenceState) -> MeasurementReceipt:
        channel_map = self.manifest.by_id()
        chosen = [c for c in self.manifest.channels if c.mandatory_sentinel]
        spent = sum(c.cost for c in chosen)
        if self._pool:
            start = evidence.as_of % len(self._pool)
            for offset in range(len(self._pool)):
                channel = channel_map[self._pool[(start + offset) % len(self._pool)]]
                if spent + channel.cost <= self.manifest.budget_per_tick:
                    chosen.append(channel)
                    spent += channel.cost
        return MeasurementReceipt(
            schema="openline.ace.dor001.measurement_receipt.v1",
            scenario_id=scenario_id,
            as_of=evidence.as_of,
            evidence_receipt_ids=tuple(r.receipt_id for r in evidence.receipts),
            selected_channels=tuple(c.channel_id for c in chosen),
            reason={c.channel_id: ("mandatory_sentinel" if c.mandatory_sentinel else "equal_budget_round_robin") for c in chosen},
            budget_limit=self.manifest.budget_per_tick,
            budget_spent=spent,
            expires_at=evidence.as_of + 1,
            runtime_permission="NONE",
        ).with_hash()


def declared_transition(receipt: MeasurementReceipt, observations: Iterable[Observation], manifest: ChannelManifest) -> bool:
    channel_map = manifest.by_id()
    selected = set(receipt.selected_channels)
    return any(
        o.channel_id in selected
        and channel_map[o.channel_id].can_resolve
        and o.value >= channel_map[o.channel_id].positive_threshold
        for o in observations
    )
