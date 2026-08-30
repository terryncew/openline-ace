from __future__ import annotations

import hashlib
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openline_assurance import AssuranceRuntime, Proposal, SignerRegistry, StandingLedger, issue_receipt


def h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.registry = SignerRegistry(
            {
                "agent": b"agent",
                "task": b"task",
                "meta": b"meta",
                "ace": b"ace",
                "principal": b"principal",
                "gate": b"gate",
                "fake-principal": b"fake-principal",
            },
            {
                "agent": "PROPOSER",
                "task": "TASK_EVALUATOR",
                "meta": "META_EVALUATOR",
                "ace": "CONSEQUENCE_EVALUATOR",
                "principal": "PRINCIPAL_AUTHORITY",
                "gate": "RECEIVER_GATE",
                "fake-principal": "TASK_EVALUATOR",
            },
        )
        self.ledger = StandingLedger()
        self.runtime = AssuranceRuntime(self.registry, self.ledger, "gate")

    def proposal(self, *, generator=False, paths=("src/x.py",)):
        return Proposal(
            proposal_id="p1",
            actor_id="agent",
            action="commit_patch",
            target="repo",
            payload_sha256=h("payload"),
            changed_paths=paths,
            mutation_tier="TIER2_GENERATOR" if generator else "TIER1_OPERATIONAL",
            generator_surface=generator,
        )

    def receipts(self, p, *, task_issuer="task", mandate_issuer="principal", task_pass=True, consequence=True, meta=False, exp=200):
        rs = [
            issue_receipt(self.registry, issuer_id=task_issuer, kind="TASK_EVALUATION", subject_id=p.proposal_id, subject_sha256=p.payload_sha256, issued_at=100, expires_at=exp, claims={"passed": task_pass}),
            issue_receipt(self.registry, issuer_id="ace", kind="CONSEQUENCE", subject_id=p.proposal_id, subject_sha256=p.payload_sha256, issued_at=100, expires_at=exp, claims={"acceptable": consequence}),
            issue_receipt(self.registry, issuer_id=mandate_issuer, kind="MANDATE", subject_id=p.proposal_id, subject_sha256=p.payload_sha256, issued_at=90, expires_at=exp, claims={"allowed_actions": ["commit_patch"], "allowed_path_prefixes": ["src/", "agent/"]}),
        ]
        if meta:
            rs.append(issue_receipt(self.registry, issuer_id="meta", kind="META_EVALUATION", subject_id=p.proposal_id, subject_sha256=p.payload_sha256, issued_at=100, expires_at=exp, claims={"passed": True}))
        return rs

    def test_valid_patch_commits(self):
        p = self.proposal()
        d = self.runtime.adjudicate(p, self.receipts(p), now=110)
        self.assertEqual("COMMIT", d.disposition)

    def test_agent_cannot_manufacture_task_evidence(self):
        p = self.proposal()
        rs = self.receipts(p)
        forged = issue_receipt(self.registry, issuer_id="agent", kind="TASK_EVALUATION", subject_id=p.proposal_id, subject_sha256=p.payload_sha256, issued_at=100, expires_at=200, claims={"passed": True})
        rs[0] = forged
        d = self.runtime.adjudicate(p, rs, now=110)
        self.assertEqual("DENY", d.disposition)
        self.assertIn("SELF_ISSUED:TASK_EVALUATION", d.reasons)

    def test_evaluator_cannot_grant_authority(self):
        p = self.proposal()
        rs = self.receipts(p, mandate_issuer="fake-principal")
        d = self.runtime.adjudicate(p, rs, now=110)
        self.assertEqual("DENY", d.disposition)
        self.assertIn("WRONG_ROLE:MANDATE", d.reasons)

    def test_expired_receipt_quarantines(self):
        p = self.proposal()
        d = self.runtime.adjudicate(p, self.receipts(p, exp=105), now=110)
        self.assertEqual("QUARANTINE", d.disposition)

    def test_out_of_scope_path_denied(self):
        p = self.proposal(paths=(".github/workflows/release.yml",))
        d = self.runtime.adjudicate(p, self.receipts(p), now=110)
        self.assertEqual("DENY", d.disposition)
        self.assertTrue(any(r.startswith("PATH_OUT_OF_MANDATE") for r in d.reasons))

    def test_generator_change_requires_meta_evaluator(self):
        p = self.proposal(generator=True, paths=("agent/search/policy.py",))
        d = self.runtime.adjudicate(p, self.receipts(p, meta=False), now=110)
        self.assertEqual("QUARANTINE", d.disposition)
        self.assertIn("MISSING:META_EVALUATION", d.reasons)

    def test_generator_change_commits_with_separate_meta_evaluator(self):
        p = self.proposal(generator=True, paths=("agent/search/policy.py",))
        d = self.runtime.adjudicate(p, self.receipts(p, meta=True), now=110)
        self.assertEqual("COMMIT", d.disposition)

    def test_boundary_laundering_defaults_to_generator_tier(self):
        p = self.proposal(generator=False, paths=("agent/search/policy.py",))
        d = self.runtime.adjudicate(p, self.receipts(p, meta=False), now=110)
        self.assertEqual("QUARANTINE", d.disposition)
        self.assertIn("MISSING:META_EVALUATION", d.reasons)

    def test_tampered_receipt_denied(self):
        p = self.proposal()
        rs = self.receipts(p)
        rs[0] = replace(rs[0], claims={"passed": False})
        d = self.runtime.adjudicate(p, rs, now=110)
        self.assertEqual("DENY", d.disposition)
        self.assertIn("INVALID_SIGNATURE:TASK_EVALUATION", d.reasons)

    def test_standing_loss_reopens_historical_commit(self):
        p = self.proposal()
        rs = self.receipts(p)
        d = self.runtime.adjudicate(p, rs, now=110)
        self.assertEqual("COMMIT", d.disposition)
        event = self.runtime.lose_standing(rs[0].receipt_id)
        self.assertIn(d.decision_id, event.reopened_decision_ids)

    def test_historical_commit_does_not_self_authorize_after_revocation(self):
        p = self.proposal()
        rs = self.receipts(p)
        d1 = self.runtime.adjudicate(p, rs, now=110)
        self.assertEqual("COMMIT", d1.disposition)
        self.runtime.lose_standing(rs[2].receipt_id)
        d2 = self.runtime.adjudicate(p, rs, now=111)
        self.assertEqual("DENY", d2.disposition)
        self.assertIn("INACTIVE_STANDING:MANDATE", d2.reasons)


if __name__ == "__main__":
    unittest.main()
