from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


FORBIDDEN_PROPOSER_KEYS = {
    "artifact_valid",
    "expected_standing",
    "ground_truth",
    "hidden_fault",
    "hidden_faults",
    "oracle_label",
    "standing",
    "verdict",
}


@dataclass(frozen=True)
class AuditPolicy:
    min_pairs: int = 64
    effect_margin: float = 0.20
    equivalence_band: float = 0.08
    sham_failure_ceiling: float = 0.20
    baseline_success_floor: float = 0.75
    bootstrap_samples: int = 5000
    bootstrap_alpha: float = 0.05

    def as_dict(self) -> dict[str, Any]:
        return {
            "min_pairs": self.min_pairs,
            "effect_margin": self.effect_margin,
            "equivalence_band": self.equivalence_band,
            "sham_failure_ceiling": self.sham_failure_ceiling,
            "baseline_success_floor": self.baseline_success_floor,
            "bootstrap_samples": self.bootstrap_samples,
            "bootstrap_alpha": self.bootstrap_alpha,
        }


@dataclass(frozen=True)
class ArmResult:
    candidate_id: str
    pair_id: str
    task_id: str
    seed: int
    arm: str
    verifier_id: str
    verifier_success: bool
    runner_status: str = "ok"
    trace_sha256: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ArmResult":
        required = {
            "candidate_id", "pair_id", "task_id", "seed", "arm",
            "verifier_id", "verifier_success"
        }
        missing = required - set(value)
        if missing:
            raise ValueError(f"missing arm result fields: {sorted(missing)}")
        if value["arm"] not in {"baseline", "active", "sham", "restoration"}:
            raise ValueError("invalid arm")
        if type(value["verifier_success"]) is not bool:
            raise ValueError("verifier_success must be bool")
        return cls(
            candidate_id=str(value["candidate_id"]),
            pair_id=str(value["pair_id"]),
            task_id=str(value["task_id"]),
            seed=int(value["seed"]),
            arm=str(value["arm"]),
            verifier_id=str(value["verifier_id"]),
            verifier_success=bool(value["verifier_success"]),
            runner_status=str(value.get("runner_status", "ok")),
            trace_sha256=value.get("trace_sha256"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "pair_id": self.pair_id,
            "task_id": self.task_id,
            "seed": self.seed,
            "arm": self.arm,
            "verifier_id": self.verifier_id,
            "verifier_success": self.verifier_success,
            "runner_status": self.runner_status,
            "trace_sha256": self.trace_sha256,
        }


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    required = {"candidate_id", "text", "scope", "source", "relation", "interventions"}
    missing = required - set(candidate)
    if missing:
        raise ValueError(f"missing candidate fields: {sorted(missing)}")
    hits = sorted(set(_walk_keys(candidate)) & FORBIDDEN_PROPOSER_KEYS)
    if hits:
        raise ValueError(f"proposer candidate contains forbidden adjudication fields: {hits}")
    source = candidate["source"]
    if not isinstance(source, dict) or source.get("authority") != "NONE":
        raise ValueError("candidate proposer authority must be NONE")
    interventions = candidate["interventions"]
    if not isinstance(interventions, dict):
        raise ValueError("interventions must be an object")
    if set(interventions) != {"active", "sham", "restoration"}:
        raise ValueError("candidate must define exactly active, sham, restoration")
    for arm in ("active", "sham", "restoration"):
        spec = interventions[arm]
        if not isinstance(spec, dict) or not spec.get("op"):
            raise ValueError(f"{arm} intervention must declare op")
    return dict(candidate)
