from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openline_assurance import AssuranceRuntime, Proposal, SignerRegistry, StandingLedger, issue_receipt


def payload_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def main() -> None:
    registry = SignerRegistry(
        {
            "coding-agent": b"agent-demo-key",
            "task-eval": b"task-demo-key",
            "meta-eval": b"meta-demo-key",
            "ace": b"ace-demo-key",
            "principal": b"principal-demo-key",
            "receipt-gate": b"gate-demo-key",
        },
        {
            "coding-agent": "PROPOSER",
            "task-eval": "TASK_EVALUATOR",
            "meta-eval": "META_EVALUATOR",
            "ace": "CONSEQUENCE_EVALUATOR",
            "principal": "PRINCIPAL_AUTHORITY",
            "receipt-gate": "RECEIVER_GATE",
        },
    )
    ledger = StandingLedger()
    runtime = AssuranceRuntime(registry, ledger, "receipt-gate")
    p = Proposal(
        proposal_id="patch-001",
        actor_id="coding-agent",
        action="commit_patch",
        target="repo",
        payload_sha256=payload_hash("fix parser bounds"),
        changed_paths=("src/parser.py",),
    )
    receipts = [
        issue_receipt(registry, issuer_id="task-eval", kind="TASK_EVALUATION", subject_id=p.proposal_id, subject_sha256=p.payload_sha256, issued_at=100, expires_at=200, claims={"passed": True}),
        issue_receipt(registry, issuer_id="ace", kind="CONSEQUENCE", subject_id=p.proposal_id, subject_sha256=p.payload_sha256, issued_at=100, expires_at=200, claims={"acceptable": True}),
        issue_receipt(registry, issuer_id="principal", kind="MANDATE", subject_id=p.proposal_id, subject_sha256=p.payload_sha256, issued_at=90, expires_at=300, claims={"allowed_actions": ["commit_patch"], "allowed_path_prefixes": ["src/"]}),
    ]
    decision = runtime.adjudicate(p, receipts, now=110)
    print(json.dumps({"decision": decision.disposition, "reasons": decision.reasons, "receipt": decision.receipt_id}, indent=2))
    event = runtime.lose_standing(receipts[0].receipt_id)
    print(json.dumps({"standing_loss": receipts[0].receipt_id, "reopened_decisions": event.reopened_decision_ids}, indent=2))


if __name__ == "__main__":
    main()
