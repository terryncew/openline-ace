from __future__ import annotations
from .model import ArmResult, Candidate, Nuisance, Outcome

class AgentWorkflowAdapter:
    substrate_id = "agent-handoff"
    substrate_class = "agent_software_workflow"
    current_patch = "commit-9f2a"
    def candidates(self):
        return (
            Candidate("fresh-test-binding", "Test evidence must be bound to the current patch.", "freshness_provenance"),
            Candidate("planning-marker", "A planning marker must be present before submission.", "observational_ritual"),
        )
    def _oracle(self, test_commit: str):
        return Outcome(test_commit == self.current_patch, "deterministic_patch_verifier", {"current_patch": self.current_patch, "test_commit": test_commit})
    def _run(self, c, arm):
        test_commit = self.current_patch
        if c.candidate_id == "fresh-test-binding" and arm == "active":
            test_commit = "commit-old0"
        nuisance = Nuisance(1, 0, 1) if arm in {"active", "sham"} else Nuisance(0, 0, 0)
        return ArmResult(arm, self._oracle(test_commit), nuisance)
    def baseline(self,c): return self._run(c,"baseline")
    def active(self,c): return self._run(c,"active")
    def sham(self,c): return self._run(c,"sham")
    def restoration(self,c): return self._run(c,"restoration")

class DistributedSystemAdapter:
    substrate_id = "replicated-log"
    substrate_class = "distributed_system"
    def candidates(self):
        return (
            Candidate("majority-before-commit", "An entry may be committed only after replication to a majority.", "quorum_safety"),
            Candidate("leader-audit-marker", "The leader must emit an audit marker before commit.", "observational_ritual"),
        )
    @staticmethod
    def _oracle(replica_count: int):
        return Outcome(replica_count >= 2, "replicated_log_safety_oracle", {"cluster_size": 3, "replica_count": replica_count, "majority_required": 2})
    def _run(self,c,arm):
        replicas = 1 if c.candidate_id == "majority-before-commit" and arm == "active" else 2
        nuisance = Nuisance(1, 1, 0) if arm in {"active", "sham"} else Nuisance(0, 0, 0)
        return ArmResult(arm, self._oracle(replicas), nuisance)
    def baseline(self,c): return self._run(c,"baseline")
    def active(self,c): return self._run(c,"active")
    def sham(self,c): return self._run(c,"sham")
    def restoration(self,c): return self._run(c,"restoration")

def simulate(*, stale_sensor: bool, steps: int = 14):
    x = 1.0
    frozen = x
    peak = abs(x)
    for _ in range(steps):
        observed = frozen if stale_sensor else x
        control = -0.75 * observed
        x = 1.20 * x + control
        peak = max(peak, abs(x))
    return x, peak

class ControlSimulationAdapter:
    substrate_id = "unstable-feedback-sim"
    substrate_class = "control_simulation"
    def candidates(self):
        return (
            Candidate("fresh-sensor-feedback", "Control output must depend on the current sensor state.", "sensor_freshness"),
            Candidate("telemetry-marker", "A telemetry marker must be emitted before each control update.", "observational_ritual"),
        )
    @staticmethod
    def _oracle(stale_sensor: bool):
        final_state, peak = simulate(stale_sensor=stale_sensor)
        success = abs(final_state) <= 0.05 and peak <= 5.0
        return Outcome(success, "simulated_stability_envelope", {
            "final_abs_state_micros": round(abs(final_state) * 1_000_000),
            "peak_abs_state_micros": round(peak * 1_000_000),
            "simulation_only": True,
        })
    def _run(self,c,arm):
        stale = c.candidate_id == "fresh-sensor-feedback" and arm == "active"
        nuisance = Nuisance(1, 1, 0) if arm in {"active", "sham"} else Nuisance(0, 0, 0)
        return ArmResult(arm, self._oracle(stale), nuisance)
    def baseline(self,c): return self._run(c,"baseline")
    def active(self,c): return self._run(c,"active")
    def sham(self,c): return self._run(c,"sham")
    def restoration(self,c): return self._run(c,"restoration")
