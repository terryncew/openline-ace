"""Independent Raft safety oracle.

This module consumes trace events only. It does not import the clause evaluator
or the candidate vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .trace import Trace


@dataclass(frozen=True)
class OracleReport:
    passed: bool
    properties: dict[str, bool]
    violations: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "properties": dict(self.properties),
            "violations": [dict(item) for item in self.violations],
        }


def check_raft_safety(trace: Trace) -> OracleReport:
    leaders: dict[int, set[str]] = {}
    logs: dict[str, dict[int, tuple[int, str]]] = {}
    committed: list[tuple[int, int, str, int]] = []
    applied: dict[int, set[str]] = {}
    violations: list[dict[str, Any]] = []
    leader_completeness_ok = True

    for event in trace.events:
        if event.kind == "log_write":
            index = event.get("index")
            term = event.get("term")
            digest = event.get("digest")
            logs.setdefault(event.node, {})[index] = (term, digest)
        elif event.kind == "commit_advance":
            committed.append((event.get("term"), event.get("index"), event.get("digest"), event.step))
        elif event.kind == "leader_elected":
            term = event.get("term")
            leaders.setdefault(term, set()).add(event.node)
            leader_log = logs.get(event.node, {})
            for entry_term, index, digest, commit_step in committed:
                if commit_step < event.step and term > entry_term:
                    if leader_log.get(index) != (entry_term, digest):
                        leader_completeness_ok = False
                        violations.append(
                            {
                                "property": "leader_completeness",
                                "step": event.step,
                                "leader": event.node,
                                "term": term,
                                "missing_index": index,
                            }
                        )
        elif event.kind == "apply":
            applied.setdefault(event.get("index"), set()).add(event.get("digest"))

    election_ok = True
    for term, elected in leaders.items():
        if len(elected) > 1:
            election_ok = False
            violations.append(
                {
                    "property": "election_safety",
                    "term": term,
                    "leaders": sorted(elected),
                }
            )

    log_matching_ok = True
    nodes = sorted(logs)
    for left_index, left_node in enumerate(nodes):
        for right_node in nodes[left_index + 1 :]:
            left = logs[left_node]
            right = logs[right_node]
            for index in sorted(left.keys() & right.keys()):
                if left[index][0] != right[index][0]:
                    continue
                for prefix in range(1, index + 1):
                    if left.get(prefix) != right.get(prefix):
                        log_matching_ok = False
                        violations.append(
                            {
                                "property": "log_matching",
                                "left": left_node,
                                "right": right_node,
                                "shared_index": index,
                                "mismatch_index": prefix,
                            }
                        )
                        break

    state_machine_ok = True
    for index, digests in applied.items():
        if len(digests) > 1:
            state_machine_ok = False
            violations.append(
                {
                    "property": "state_machine_safety",
                    "index": index,
                    "digests": sorted(digests),
                }
            )

    properties = {
        "election_safety": election_ok,
        "leader_completeness": leader_completeness_ok,
        "log_matching": log_matching_ok,
        "state_machine_safety": state_machine_ok,
    }
    return OracleReport(all(properties.values()), properties, tuple(violations))

