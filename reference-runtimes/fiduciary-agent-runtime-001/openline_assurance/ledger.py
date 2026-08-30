from __future__ import annotations

from collections import defaultdict, deque

from .model import GateDecision, Receipt, ReopenEvent


class StandingLedger:
    def __init__(self):
        self.receipts: dict[str, Receipt] = {}
        self.decisions: dict[str, GateDecision] = {}
        self.receipt_dependents: dict[str, set[str]] = defaultdict(set)
        self.decision_receipt: dict[str, str] = {}
        self.invalidated_receipts: set[str] = set()
        self.reopened_decisions: set[str] = set()

    def add_receipt(self, receipt: Receipt) -> None:
        self.receipts[receipt.receipt_id] = receipt
        for dep in receipt.dependencies:
            self.receipt_dependents[dep].add(receipt.receipt_id)

    def add_decision(self, decision: GateDecision) -> None:
        self.decisions[decision.decision_id] = decision
        for dep in decision.relied_on_receipts:
            self.receipt_dependents[dep].add(f"decision:{decision.decision_id}")
        if decision.receipt_id:
            self.decision_receipt[decision.decision_id] = decision.receipt_id

    def standing_active(self, receipt_id: str) -> bool:
        receipt = self.receipts.get(receipt_id)
        return bool(receipt and receipt.standing == "ACTIVE" and receipt_id not in self.invalidated_receipts)

    def invalidate(self, receipt_id: str) -> ReopenEvent:
        if receipt_id not in self.receipts:
            raise KeyError(receipt_id)
        queue = deque([receipt_id])
        seen_receipts: set[str] = set()
        reopened: set[str] = set()
        while queue:
            current = queue.popleft()
            if current in seen_receipts:
                continue
            seen_receipts.add(current)
            self.invalidated_receipts.add(current)
            for child in self.receipt_dependents.get(current, set()):
                if child.startswith("decision:"):
                    did = child.split(":", 1)[1]
                    reopened.add(did)
                    self.reopened_decisions.add(did)
                    decision_receipt = self.decision_receipt.get(did)
                    if decision_receipt:
                        queue.append(decision_receipt)
                else:
                    queue.append(child)
        return ReopenEvent(
            cause_receipt_id=receipt_id,
            reopened_decision_ids=tuple(sorted(reopened)),
            reopened_receipt_ids=tuple(sorted(seen_receipts - {receipt_id})),
        )
