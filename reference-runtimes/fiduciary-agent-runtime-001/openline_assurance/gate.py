from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import Iterable

from .canonical import sha256
from .classifier import effective_mutation_tier
from .crypto import SignerRegistry
from .ledger import StandingLedger
from .model import Disposition, GateDecision, Proposal, Receipt
from .receipts import issue_receipt


class AssuranceGate:
    def __init__(
        self,
        *,
        registry: SignerRegistry,
        ledger: StandingLedger,
        gate_signer_id: str,
        now: int,
    ):
        self.registry = registry
        self.ledger = ledger
        self.gate_signer_id = gate_signer_id
        self.now = now

    def _validate_receipt(self, receipt: Receipt, proposal: Proposal) -> list[str]:
        reasons: list[str] = []
        if not self.registry.verify(receipt):
            reasons.append(f"INVALID_SIGNATURE:{receipt.kind}")
        if receipt.subject_id != proposal.proposal_id or receipt.subject_sha256 != proposal.payload_sha256:
            reasons.append(f"SUBJECT_MISMATCH:{receipt.kind}")
        if receipt.standing != "ACTIVE" or receipt.receipt_id in self.ledger.invalidated_receipts:
            reasons.append(f"INACTIVE_STANDING:{receipt.kind}")
        if receipt.expires_at is not None and self.now > receipt.expires_at:
            reasons.append(f"EXPIRED:{receipt.kind}")
        if receipt.issuer_id == proposal.actor_id:
            reasons.append(f"SELF_ISSUED:{receipt.kind}")
        return reasons

    def decide(self, proposal: Proposal, receipts: Iterable[Receipt]) -> GateDecision:
        receipts = tuple(receipts)
        by_kind = {r.kind: r for r in receipts}
        required = {"TASK_EVALUATION", "CONSEQUENCE", "MANDATE"}
        if effective_mutation_tier(proposal) == "TIER2_GENERATOR":
            required.add("META_EVALUATION")

        missing = sorted(required - set(by_kind))
        if missing:
            return self._record(proposal, Disposition.QUARANTINE, [f"MISSING:{k}" for k in missing], receipts)

        reasons: list[str] = []
        for kind in sorted(required):
            reasons.extend(self._validate_receipt(by_kind[kind], proposal))

        roles = {
            "TASK_EVALUATION": "TASK_EVALUATOR",
            "META_EVALUATION": "META_EVALUATOR",
            "CONSEQUENCE": "CONSEQUENCE_EVALUATOR",
            "MANDATE": "PRINCIPAL_AUTHORITY",
        }
        for kind, role in roles.items():
            if kind in required and by_kind[kind].issuer_role != role:
                reasons.append(f"WRONG_ROLE:{kind}")

        evaluator_ids = {by_kind[k].issuer_id for k in required if k.endswith("EVALUATION") or k == "CONSEQUENCE"}
        mandate_id = by_kind["MANDATE"].issuer_id
        if mandate_id in evaluator_ids:
            reasons.append("AUTHORITY_EVALUATOR_COLLAPSE")

        mandate = by_kind["MANDATE"].claims
        allowed_actions = set(mandate.get("allowed_actions", []))
        allowed_prefixes = tuple(mandate.get("allowed_path_prefixes", []))
        if proposal.action not in allowed_actions:
            reasons.append("ACTION_OUT_OF_MANDATE")
        if proposal.changed_paths and allowed_prefixes:
            for path in proposal.changed_paths:
                if not any(path.startswith(prefix) for prefix in allowed_prefixes):
                    reasons.append(f"PATH_OUT_OF_MANDATE:{path}")

        if by_kind["TASK_EVALUATION"].claims.get("passed") is not True:
            reasons.append("TASK_EVALUATION_FAILED")
        if by_kind["CONSEQUENCE"].claims.get("acceptable") is not True:
            reasons.append("CONSEQUENCE_NOT_ACCEPTABLE")
        if "META_EVALUATION" in required and by_kind["META_EVALUATION"].claims.get("passed") is not True:
            reasons.append("META_EVALUATION_FAILED")

        hard = [r for r in reasons if not r.startswith("EXPIRED:")]
        if hard:
            return self._record(proposal, Disposition.DENY, sorted(set(reasons)), receipts)
        if reasons:
            return self._record(proposal, Disposition.QUARANTINE, sorted(set(reasons)), receipts)
        return self._record(proposal, Disposition.COMMIT, [], receipts)

    def _record(self, proposal: Proposal, disposition: Disposition, reasons: list[str], receipts: tuple[Receipt, ...]) -> GateDecision:
        decision_id = str(uuid.uuid4())
        relied = tuple(sorted(r.receipt_id for r in receipts))
        decision_receipt = issue_receipt(
            self.registry,
            issuer_id=self.gate_signer_id,
            kind="GATE_DECISION",
            subject_id=proposal.proposal_id,
            subject_sha256=proposal.payload_sha256,
            issued_at=self.now,
            expires_at=None,
            claims={
                "decision_id": decision_id,
                "disposition": disposition.value,
                "reasons": reasons,
                "proposal_sha256": sha256(asdict(proposal)),
            },
            dependencies=relied,
        )
        self.ledger.add_receipt(decision_receipt)
        decision = GateDecision(
            decision_id=decision_id,
            proposal_id=proposal.proposal_id,
            disposition=disposition.value,
            reasons=tuple(reasons),
            relied_on_receipts=relied,
            receipt_id=decision_receipt.receipt_id,
        )
        self.ledger.add_decision(decision)
        return decision
