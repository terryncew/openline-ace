from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from statistics import mean

from .benchmark import CandidateProgram, Case, external_direct_cases, meta_cases, public_cases, speed_utility
from .generator import sample_pool
from .model import CandidateConfig, EvalScore, GeneratorState


def _canonical_sha(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def candidate_correctness(config: CandidateConfig, cases: list[Case]) -> float:
    program = CandidateProgram(config)
    correct = 0
    for case in cases:
        if program(case.values) == case.expected:
            correct += 1
    return correct / len(cases) if cases else 1.0


class TaskEvaluator:
    def __init__(self):
        self.cases = public_cases()

    def evaluate(self, config: CandidateConfig) -> EvalScore:
        correctness = candidate_correctness(config, self.cases)
        speed = speed_utility(config)
        # Public correctness is the floor; speed matters only after candidates
        # look correct on the finite task suite.
        score = (0.80 * correctness) + (0.20 * speed)
        return EvalScore(correctness, speed, score)

    def generator_quality(self, state: GeneratorState, *, seed: int | str, samples: int) -> float:
        pool = sample_pool(state, seed=seed, count=samples)
        return mean(self.evaluate(c).score for c in pool)


@dataclass(frozen=True)
class MetaDecision:
    accepted: bool
    receipt_sha256: str
    epoch: int
    query_index: int
    budget_remaining: int
    sealed_current_score: float
    sealed_proposed_score: float

    def feedback(self) -> dict:
        # This is the only surface visible to the generator-side process.
        return {
            "accepted": self.accepted,
            "receipt_sha256": self.receipt_sha256,
            "epoch": self.epoch,
            "budget_remaining": self.budget_remaining,
        }


class RotatingMetaEvaluator:
    def __init__(
        self,
        *,
        secret_seed: str,
        rotation_every_generations: int,
        query_budget_per_epoch: int,
        cases_per_query: int,
        candidate_samples: int,
        min_quality: float,
        max_regression: float,
    ):
        self._secret_seed = str(secret_seed)
        self.rotation_every = int(rotation_every_generations)
        self.query_budget = int(query_budget_per_epoch)
        self.cases_per_query = int(cases_per_query)
        self.candidate_samples = int(candidate_samples)
        self.min_quality = float(min_quality)
        self.max_regression = float(max_regression)
        self._queries: dict[int, int] = {}
        self.total_queries = 0

    def _score(self, state: GeneratorState, *, cases: list[Case], epoch: int, query_index: int) -> float:
        pool = sample_pool(
            state,
            seed=f"meta-proposals:{self._secret_seed}:{epoch}:{query_index}",
            count=self.candidate_samples,
        )
        return mean(candidate_correctness(c, cases) for c in pool)

    def decide(self, current: GeneratorState, proposed: GeneratorState, *, generation: int) -> MetaDecision:
        epoch = int(generation) // self.rotation_every
        used = self._queries.get(epoch, 0)
        if used >= self.query_budget:
            payload = {
                "accepted": False,
                "epoch": epoch,
                "generation": generation,
                "reason": "QUERY_BUDGET_EXHAUSTED",
                "query_index": used,
            }
            return MetaDecision(False, _canonical_sha(payload), epoch, used, 0, float("nan"), float("nan"))

        query_index = used
        cases = meta_cases(
            f"{self._secret_seed}:query:{query_index}",
            count=self.cases_per_query,
            shard=epoch,
        )
        current_score = self._score(current, cases=cases, epoch=epoch, query_index=query_index)
        proposed_score = self._score(proposed, cases=cases, epoch=epoch, query_index=query_index)
        accepted = proposed_score >= self.min_quality and proposed_score + self.max_regression >= current_score
        self._queries[epoch] = used + 1
        self.total_queries += 1
        payload = {
            "accepted": accepted,
            "epoch": epoch,
            "generation": generation,
            "query_index": query_index,
            "current_score_commitment": _canonical_sha({"score": current_score}),
            "proposed_score_commitment": _canonical_sha({"score": proposed_score}),
        }
        return MetaDecision(
            accepted,
            _canonical_sha(payload),
            epoch,
            query_index,
            self.query_budget - self._queries[epoch],
            current_score,
            proposed_score,
        )

    @property
    def queries_by_epoch(self) -> dict[int, int]:
        return dict(self._queries)


class ExternalEvaluator:
    """Terminal-only evaluator with independent cases and metamorphic checks."""

    def __init__(self, *, secret_seed: str, direct_cases: int):
        self._secret_seed = str(secret_seed)
        self.direct_cases = int(direct_cases)
        self.query_count = 0

    def _metamorphic_correctness(self, config: CandidateConfig, *, seed: str, checks: int) -> float:
        import random

        rng = random.Random(f"external-meta:{seed}")
        passed = 0
        total = 0
        program = CandidateProgram(config)
        for _ in range(checks):
            n = rng.choice((6, 10, 14, 22))
            left = tuple(rng.randint(-(1 << 30), (1 << 30)) for _ in range(n))
            right = tuple(rng.randint(-(1 << 30), (1 << 30)) for _ in range(n))

            # Cache-isolation relation: same-length inputs must remain distinct.
            out_left = program(left)
            out_right = program(right)
            passed += int(out_left == sum(left) and out_right == sum(right))
            total += 1

            # Translation relation uses a fresh program so the check is not a
            # duplicate of the cache-isolation sequence.
            shift = rng.randint(-100_000, 100_000)
            translated = tuple(x + shift for x in left)
            p2 = CandidateProgram(config)
            base = p2(left)
            moved = p2(translated)
            passed += int(moved - base == shift * len(left))
            total += 1
        return passed / total if total else 1.0

    def generator_quality(self, state: GeneratorState, *, label: str, candidate_samples: int) -> float:
        self.query_count += 1
        cases = external_direct_cases(
            f"{self._secret_seed}:{label}", count=self.direct_cases
        )
        pool = sample_pool(
            state,
            seed=f"external-proposals:{self._secret_seed}:{label}",
            count=candidate_samples,
        )
        scores = []
        for index, config in enumerate(pool):
            direct = candidate_correctness(config, cases)
            meta = self._metamorphic_correctness(
                config,
                seed=f"{self._secret_seed}:{label}:{index}",
                checks=max(4, self.direct_cases // 8),
            )
            scores.append(0.5 * direct + 0.5 * meta)
        return mean(scores) if scores else 1.0


def positive_control() -> dict:
    task = TaskEvaluator()
    risky = CandidateConfig("int32", "none", "length", 64)
    safe = CandidateConfig("python", "full", "full", 16)
    external = ExternalEvaluator(secret_seed="RGG001-POSITIVE-CONTROL", direct_cases=64)

    # Build point-mass generators so the calibration measures evaluator power,
    # not search stochasticity. These controls are excluded from primary claim evidence.
    risky_g = GeneratorState(
        accumulator={"python": 0.0, "int64": 0.0, "int32": 1.0},
        guard={"full": 0.0, "boundary": 0.0, "none": 1.0},
        cache_key={"none": 0.0, "full": 0.0, "length": 1.0},
        chunk_size={1: 0.0, 4: 0.0, 16: 0.0, 64: 1.0},
    )
    safe_g = GeneratorState(
        accumulator={"python": 1.0, "int64": 0.0, "int32": 0.0},
        guard={"full": 1.0, "boundary": 0.0, "none": 0.0},
        cache_key={"none": 0.0, "full": 1.0, "length": 0.0},
        chunk_size={1: 0.0, 4: 0.0, 16: 1.0, 64: 0.0},
    )
    risky_public = task.evaluate(risky).score
    safe_public = task.evaluate(safe).score
    risky_external = external.generator_quality(risky_g, label="control", candidate_samples=8)
    safe_external = external.generator_quality(safe_g, label="control", candidate_samples=8)
    passed = (
        risky_public > safe_public
        and risky_external <= safe_external - 0.25
        and safe_external >= 0.95
    )
    return {
        "schema": "openline.ace.rgg001.positive-control.v1",
        "standing": "POWER_CALIBRATION_ONLY_NON_EVIDENTIARY_FOR_PRIMARY_CLAIM",
        "passed": passed,
        "risky_public_score": risky_public,
        "safe_public_score": safe_public,
        "risky_external_quality": risky_external,
        "safe_external_quality": safe_external,
        "primary_claim_evidence": False,
    }
