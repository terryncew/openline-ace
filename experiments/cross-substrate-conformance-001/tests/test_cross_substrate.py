from __future__ import annotations
import unittest
from ace_xs.fixtures import AgentWorkflowAdapter, DistributedSystemAdapter, ControlSimulationAdapter, simulate
from ace_xs.model import ArmResult, Candidate, Nuisance, Outcome
from ace_xs.protocol import audit_adapter, grade_candidate
from ace_xs.run import build_result

class CrossSubstrateTests(unittest.TestCase):
    def test_exact_three_true_dependencies_survive(self):
        result = build_result()
        supported = {r["candidate"]["candidate_id"] for r in result["records"] if r["grade"]["standing"] == "SUPPORTED"}
        self.assertEqual(supported, {"fresh-test-binding", "majority-before-commit", "fresh-sensor-feedback"})

    def test_exact_three_perfect_rituals_are_rejected(self):
        result = build_result()
        rituals = {r["candidate"]["candidate_id"] for r in result["records"] if r["grade"]["standing"] == "REJECTED_RITUAL"}
        self.assertEqual(rituals, {"planning-marker", "leader-audit-marker", "telemetry-marker"})

    def test_same_grader_handles_every_substrate(self):
        for adapter in (AgentWorkflowAdapter(), DistributedSystemAdapter(), ControlSimulationAdapter()):
            records = audit_adapter(adapter)
            self.assertEqual({r.grade.standing for r in records}, {"SUPPORTED", "REJECTED_RITUAL"})

    def test_sham_mismatch_forces_abstention(self):
        c = Candidate("c", "candidate", "test")
        base = ArmResult("baseline", Outcome(True, "o", {}), Nuisance(0,0,0))
        active = ArmResult("active", Outcome(False, "o", {}), Nuisance(1,1,0))
        sham = ArmResult("sham", Outcome(True, "o", {}), Nuisance(1,0,0))
        restore = ArmResult("restoration", Outcome(True, "o", {}), Nuisance(0,0,0))
        grade = grade_candidate(c, baseline=base, active=active, sham=sham, restoration=restore)
        self.assertEqual((grade.standing, grade.reason), ("UNDECIDABLE", "SHAM_NOT_MATCHED"))

    def test_failed_restoration_cannot_support(self):
        c = Candidate("c", "candidate", "test")
        zero = Nuisance(0,0,0); one = Nuisance(1,0,0)
        grade = grade_candidate(
            c,
            baseline=ArmResult("baseline", Outcome(True, "o", {}), zero),
            active=ArmResult("active", Outcome(False, "o", {}), one),
            sham=ArmResult("sham", Outcome(True, "o", {}), one),
            restoration=ArmResult("restoration", Outcome(False, "o", {}), zero),
        )
        self.assertEqual(grade.standing, "UNDECIDABLE")

    def test_control_is_explicitly_simulation_only(self):
        result = build_result()
        self.assertIn("Control specimen is simulation only; no physical robotics claim.", result["claim_boundary"])
        for row in result["records"]:
            if row["substrate_class"] == "control_simulation":
                self.assertTrue(row["baseline"]["details"]["simulation_only"])

    def test_control_dynamics_discriminate_fresh_vs_frozen_sensor(self):
        current_final, _ = simulate(stale_sensor=False)
        stale_final, _ = simulate(stale_sensor=True)
        self.assertLess(abs(current_final), 0.05)
        self.assertGreater(abs(stale_final), 0.05)

    def test_result_never_exports_authority(self):
        result = build_result()
        self.assertEqual(result["policy_authority"], "NONE")
        self.assertEqual(result["runtime_permission"], "NONE")

    def test_conformance_verdict_passes(self):
        result = build_result()
        self.assertEqual(result["status"], "CROSS_SUBSTRATE_CONFORMANCE_PASS")
        self.assertEqual((result["candidate_count"], result["supported_count"], result["ritual_rejected_count"], result["undecidable_count"]), (6,3,3,0))

if __name__ == "__main__":
    unittest.main()
