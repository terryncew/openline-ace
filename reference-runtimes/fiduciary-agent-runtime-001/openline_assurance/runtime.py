from __future__ import annotations

from dataclasses import dataclass

from .crypto import SignerRegistry
from .gate import AssuranceGate
from .ledger import StandingLedger
from .model import GateDecision, Proposal, Receipt, ReopenEvent


@dataclass
class AssuranceRuntime:
    registry: SignerRegistry
    ledger: StandingLedger
    gate_signer_id: str

    def adjudicate(self, proposal: Proposal, receipts: list[Receipt], *, now: int) -> GateDecision:
        for receipt in receipts:
            self.ledger.add_receipt(receipt)
        return AssuranceGate(
            registry=self.registry,
            ledger=self.ledger,
            gate_signer_id=self.gate_signer_id,
            now=now,
        ).decide(proposal, receipts)

    def lose_standing(self, receipt_id: str) -> ReopenEvent:
        return self.ledger.invalidate(receipt_id)
