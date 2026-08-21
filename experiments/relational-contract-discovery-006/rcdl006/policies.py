"""Equal-budget symbolic and learned decision policies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .model import PolicyDecision, QueryTranscript, Standing


def symbolic_decision(transcript: QueryTranscript) -> PolicyDecision:
    active, artifact, sham, restored, horizon = transcript.signature()
    if transcript.query_count != 3 or not sham or not restored:
        return PolicyDecision(Standing.INVALID, horizon, "INVALID_CONTROL_OR_RECOVERY")
    if not active and not artifact and horizon > 0:
        return PolicyDecision(Standing.SUPPORTED_NATIVE, horizon, "VERIFIER_FAILURE_AND_ARTIFACT_BREAK")
    if not active and artifact and horizon > 0:
        return PolicyDecision(Standing.REJECTED_IMPOSED, horizon, "WRAPPER_ONLY_FAILURE")
    if active and artifact and horizon == 0:
        return PolicyDecision(Standing.REJECTED_NUISANCE, 0, "NUISANCE_INVARIANT")
    return PolicyDecision(Standing.INVALID, horizon, "UNDECLARED_SIGNATURE")


@dataclass(frozen=True)
class LearnedSignaturePolicy:
    table: dict[tuple[bool, bool, bool, bool, int], PolicyDecision]
    name: str = "learned-signature-baseline"

    def decide(self, transcript: QueryTranscript) -> PolicyDecision:
        return self.table.get(
            transcript.signature(),
            PolicyDecision(Standing.INVALID, 0, "UNSEEN_SIGNATURE"),
        )


def train_learned_policy(
    examples: Iterable[tuple[QueryTranscript, Standing]],
) -> LearnedSignaturePolicy:
    table: dict[tuple[bool, bool, bool, bool, int], PolicyDecision] = {}
    for transcript, expected in examples:
        signature = transcript.signature()
        decision = PolicyDecision(expected, signature[-1], "LEARNED_DEVELOPMENT_SIGNATURE")
        previous = table.get(signature)
        if previous is not None and previous.standing is not expected:
            raise ValueError("conflicting development signatures")
        table[signature] = decision
    if len(table) != 3 or {item.standing for item in table.values()} != {
        Standing.SUPPORTED_NATIVE,
        Standing.REJECTED_IMPOSED,
        Standing.REJECTED_NUISANCE,
    }:
        raise ValueError("development training surface is incomplete")
    return LearnedSignaturePolicy(table)


def policy_boundary() -> dict[str, object]:
    return {
        "equal_query_budget": True,
        "learned_inputs": ["active outcome", "sham outcome", "restoration outcome", "recovery horizon"],
        "learned_oracle_access": False,
        "learned_proposal_id_access": False,
        "symbolic_oracle_access": False,
        "symbolic_proposal_id_access": False,
        "valid": True,
    }
