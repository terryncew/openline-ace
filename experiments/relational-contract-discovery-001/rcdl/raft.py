"""Deterministic Raft calibration substrate and frozen candidate vocabulary."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from .model import Clause
from .trace import TRACE_SCHEMA, Trace


def _intervention(hook: str) -> dict[str, Any]:
    return {
        "hook": hook,
        "active": "bypass_guard",
        "sham": "metadata_noop",
        "energy": 1,
    }


def raft_candidate_clauses() -> tuple[Clause, ...]:
    """Return the frozen, action-addressable RCDL 0.1 Raft candidates."""

    documents = [
        {
            "schema": "rcdl.clause/0.1",
            "id": "raft.vote_once_per_term",
            "kind": "integrity",
            "description": "A voter grants at most one candidate a vote in a term.",
            "trigger": {"event": "vote_reply", "where": {"granted": True}},
            "require": {
                "op": "unique_per_key",
                "key": ["node", "term"],
                "value": ["candidate"],
            },
            "intervention": _intervention("vote_once_guard"),
        },
        {
            "schema": "rcdl.clause/0.1",
            "id": "raft.vote_persisted_before_reply",
            "kind": "order",
            "description": "A granted vote is durable before its positive reply is emitted.",
            "trigger": {"event": "vote_reply", "where": {"granted": True}},
            "require": {
                "op": "exists_before",
                "event": "durable_write",
                "where": {"field": "voted_for"},
                "joins": {"node": "node", "term": "term", "candidate": "candidate"},
            },
            "intervention": _intervention("vote_persist_guard"),
        },
        {
            "schema": "rcdl.clause/0.1",
            "id": "raft.vote_requires_fresh_log",
            "kind": "guard",
            "description": "A granted vote follows a successful candidate-log freshness check.",
            "trigger": {"event": "vote_reply", "where": {"granted": True}},
            "require": {
                "op": "exists_before",
                "event": "vote_log_check",
                "where": {"result": True},
                "joins": {"node": "node", "term": "term", "candidate": "candidate"},
            },
            "intervention": _intervention("vote_fresh_log_guard"),
        },
        {
            "schema": "rcdl.clause/0.1",
            "id": "raft.append_requires_matching_prefix",
            "kind": "guard",
            "description": "An accepted append follows a matching previous log position and term.",
            "trigger": {"event": "append_accept"},
            "require": {
                "op": "exists_before",
                "event": "append_prev_check",
                "where": {"result": True},
                "joins": {
                    "node": "node",
                    "leader": "leader",
                    "prev_index": "prev_index",
                    "prev_term": "prev_term",
                },
            },
            "intervention": _intervention("append_prefix_guard"),
        },
        {
            "schema": "rcdl.clause/0.1",
            "id": "raft.commit_requires_majority",
            "kind": "guard",
            "description": "Commit advancement follows matching acknowledgements from a majority.",
            "trigger": {"event": "commit_advance"},
            "require": {
                "op": "count_distinct_before",
                "event": "replication_ack",
                "joins": {
                    "leader": "node",
                    "term": "term",
                    "index": "index",
                    "digest": "digest",
                },
                "distinct": "node",
                "threshold": {"op": "majority", "field": "cluster_size"},
            },
            "intervention": _intervention("commit_majority_guard"),
        },
        {
            "schema": "rcdl.clause/0.1",
            "id": "raft.apply_requires_commit",
            "kind": "order",
            "description": "An applied entry follows a matching commit event.",
            "trigger": {"event": "apply"},
            "require": {
                "op": "exists_before",
                "event": "commit_advance",
                "joins": {"term": "term", "index": "index", "digest": "digest"},
            },
            "intervention": _intervention("apply_commit_guard"),
        },
        {
            "schema": "rcdl.clause/0.1",
            "id": "raft.commit_audit_marker_before_commit",
            "kind": "order",
            "description": (
                "A local audit marker precedes commit advancement; this is a frozen "
                "spurious-control candidate, not a Raft requirement."
            ),
            "trigger": {"event": "commit_advance"},
            "require": {
                "op": "exists_before",
                "event": "commit_audit_marker",
                "joins": {
                    "node": "node",
                    "term": "term",
                    "index": "index",
                    "digest": "digest",
                },
            },
            "intervention": _intervention("commit_audit_guard"),
        },
    ]
    return tuple(Clause.from_dict(document) for document in documents)


ALL_HOOKS = frozenset(clause.hook for clause in raft_candidate_clauses())
SAFETY_CLAUSE_IDS = frozenset(
    {
        "raft.vote_once_per_term",
        "raft.vote_persisted_before_reply",
        "raft.vote_requires_fresh_log",
        "raft.append_requires_matching_prefix",
        "raft.commit_requires_majority",
        "raft.apply_requires_commit",
    }
)
SPURIOUS_CONTROL_IDS = frozenset({"raft.commit_audit_marker_before_commit"})
HOOK_SCENARIOS = {
    "vote_once_guard": "double_vote",
    "vote_persist_guard": "crash_after_vote",
    "vote_fresh_log_guard": "stale_candidate",
    "append_prefix_guard": "mismatched_append",
    "commit_majority_guard": "minority_commit",
    "apply_commit_guard": "uncommitted_apply",
    "commit_audit_guard": "minority_commit",
}


@dataclass
class LogEntry:
    index: int
    term: int
    digest: str


@dataclass
class NodeState:
    durable_votes: dict[int, str] = field(default_factory=dict)
    volatile_votes: dict[int, str] = field(default_factory=dict)
    log: dict[int, LogEntry] = field(default_factory=dict)
    commit_index: int = 0
    applied: dict[int, str] = field(default_factory=dict)


class TraceBuilder:
    def __init__(self, run_id: str, metadata: dict[str, Any]):
        self.run_id = run_id
        self.metadata = metadata
        self.events: list[dict[str, Any]] = []

    def emit(self, node: str, kind: str, **attrs: Any) -> None:
        step = len(self.events)
        self.events.append(
            {
                "event_id": f"e{step:04d}",
                "step": step,
                "node": node,
                "kind": kind,
                "attrs": attrs,
            }
        )

    def trace(self) -> Trace:
        return Trace.from_dict(
            {
                "schema": TRACE_SCHEMA,
                "run_id": self.run_id,
                "metadata": self.metadata,
                "events": self.events,
            }
        )


class RaftHarness:
    """Small deterministic state machine designed for intervention calibration."""

    def __init__(
        self,
        scenario: str,
        seed: int,
        enabled_hooks: frozenset[str] = ALL_HOOKS,
        arm: str = "baseline",
        target_hook: str | None = None,
    ):
        if not enabled_hooks <= ALL_HOOKS:
            raise ValueError("unknown enabled hook")
        if arm not in {"baseline", "active", "sham", "family"}:
            raise ValueError("invalid arm")
        rng = random.Random(seed)
        names = ["n0", "n1", "n2"]
        rng.shuffle(names)
        self.nodes = names
        self.states = {name: NodeState() for name in names}
        self.enabled_hooks = enabled_hooks
        self.seed = seed
        self.scenario = scenario
        self.builder = TraceBuilder(
            run_id=f"raft-{scenario}-{arm}-{seed}",
            metadata={
                "cluster_size": 3,
                "scenario": scenario,
                "seed": seed,
                "arm": arm,
                "stable_majority": True,
                "fair_delivery": True,
            },
        )
        if arm in {"active", "sham"}:
            if target_hook is None:
                raise ValueError("target hook required for active and sham arms")
            self.builder.emit(
                "system",
                "intervention",
                hook=target_hook,
                arm=arm,
                energy=1,
            )

    @property
    def majority(self) -> int:
        return len(self.nodes) // 2 + 1

    def seed_log(self, node: str, index: int, term: int, digest: str) -> None:
        self.states[node].log[index] = LogEntry(index, term, digest)
        self.builder.emit(node, "log_write", index=index, term=term, digest=digest)

    def restart(self, node: str) -> None:
        state = self.states[node]
        state.volatile_votes = dict(state.durable_votes)
        self.builder.emit(node, "restart", recovered_votes=len(state.volatile_votes))

    def request_vote(
        self,
        voter: str,
        candidate: str,
        term: int,
        candidate_fresh: bool = True,
    ) -> bool:
        state = self.states[voter]
        self.builder.emit(
            voter,
            "vote_log_check",
            candidate=candidate,
            term=term,
            result=candidate_fresh,
        )
        already = state.volatile_votes.get(term)
        allowed_once = already is None or already == candidate
        granted = True
        if "vote_once_guard" in self.enabled_hooks and not allowed_once:
            granted = False
        if "vote_fresh_log_guard" in self.enabled_hooks and not candidate_fresh:
            granted = False
        if granted:
            state.volatile_votes[term] = candidate
            if "vote_persist_guard" in self.enabled_hooks:
                state.durable_votes[term] = candidate
                self.builder.emit(
                    voter,
                    "durable_write",
                    field="voted_for",
                    term=term,
                    candidate=candidate,
                )
        self.builder.emit(
            voter,
            "vote_reply",
            candidate=candidate,
            term=term,
            granted=granted,
        )
        return granted

    def elect(
        self,
        candidate: str,
        term: int,
        voters: list[str],
        freshness: dict[str, bool] | None = None,
    ) -> bool:
        freshness = freshness or {}
        granted = [
            voter
            for voter in voters
            if self.request_vote(voter, candidate, term, freshness.get(voter, True))
        ]
        if len(granted) >= self.majority:
            self.builder.emit(candidate, "leader_elected", term=term, vote_count=len(granted))
            return True
        return False

    def append(
        self,
        receiver: str,
        leader: str,
        leader_term: int,
        prev_index: int,
        prev_term: int,
        entry: LogEntry,
    ) -> bool:
        current = self.states[receiver].log.get(prev_index)
        matched = prev_index == 0 or (current is not None and current.term == prev_term)
        self.builder.emit(
            receiver,
            "append_prev_check",
            leader=leader,
            term=leader_term,
            prev_index=prev_index,
            prev_term=prev_term,
            result=matched,
        )
        if not matched and "append_prefix_guard" in self.enabled_hooks:
            self.builder.emit(
                receiver,
                "append_reject",
                leader=leader,
                term=leader_term,
                prev_index=prev_index,
                prev_term=prev_term,
            )
            return False
        self.states[receiver].log[entry.index] = entry
        self.builder.emit(
            receiver,
            "append_accept",
            leader=leader,
            term=leader_term,
            prev_index=prev_index,
            prev_term=prev_term,
            index=entry.index,
            entry_term=entry.term,
            digest=entry.digest,
        )
        self.builder.emit(
            receiver,
            "log_write",
            index=entry.index,
            term=entry.term,
            digest=entry.digest,
        )
        return True

    def ack(self, node: str, leader: str, entry: LogEntry) -> None:
        self.builder.emit(
            node,
            "replication_ack",
            leader=leader,
            term=entry.term,
            index=entry.index,
            digest=entry.digest,
        )

    def commit(self, leader: str, entry: LogEntry, acknowledgers: list[str]) -> bool:
        for node in acknowledgers:
            self.ack(node, leader, entry)
        if len(set(acknowledgers)) < self.majority and "commit_majority_guard" in self.enabled_hooks:
            self.builder.emit(
                leader,
                "commit_reject",
                term=entry.term,
                index=entry.index,
                digest=entry.digest,
                ack_count=len(set(acknowledgers)),
            )
            return False
        if "commit_audit_guard" in self.enabled_hooks:
            self.builder.emit(
                leader,
                "commit_audit_marker",
                term=entry.term,
                index=entry.index,
                digest=entry.digest,
            )
        self.states[leader].commit_index = max(self.states[leader].commit_index, entry.index)
        self.builder.emit(
            leader,
            "commit_advance",
            term=entry.term,
            index=entry.index,
            digest=entry.digest,
            ack_count=len(set(acknowledgers)),
        )
        return True

    def apply(self, node: str, entry: LogEntry) -> bool:
        committed = any(
            event["kind"] == "commit_advance"
            and event["attrs"].get("index") == entry.index
            and event["attrs"].get("term") == entry.term
            and event["attrs"].get("digest") == entry.digest
            for event in self.builder.events
        )
        if not committed and "apply_commit_guard" in self.enabled_hooks:
            self.builder.emit(
                node,
                "apply_reject",
                term=entry.term,
                index=entry.index,
                digest=entry.digest,
            )
            return False
        self.states[node].applied[entry.index] = entry.digest
        self.builder.emit(
            node,
            "apply",
            term=entry.term,
            index=entry.index,
            digest=entry.digest,
        )
        return True

    def healthy(self) -> None:
        a, b, _ = self.nodes
        self.elect(a, 1, [a, b])
        entry = LogEntry(1, 1, f"healthy-{self.seed}")
        self.seed_log(a, 1, 1, entry.digest)
        if self.append(b, a, 1, 0, 0, entry):
            self.commit(a, entry, [a, b])
            self.apply(a, entry)
            self.apply(b, entry)

    def double_vote(self) -> None:
        a, b, c = self.nodes
        self.elect(a, 1, [a, b])
        self.elect(c, 1, [c, b])

    def crash_after_vote(self) -> None:
        a, b, c = self.nodes
        self.elect(a, 1, [a, b])
        self.restart(b)
        self.elect(c, 1, [c, b])

    def stale_candidate(self) -> None:
        a, b, c = self.nodes
        entry = LogEntry(1, 1, f"committed-{self.seed}")
        self.seed_log(a, 1, 1, entry.digest)
        self.seed_log(b, 1, 1, entry.digest)
        self.commit(a, entry, [a, b])
        self.elect(c, 2, [c, b], freshness={c: True, b: False})

    def mismatched_append(self) -> None:
        a, b, _ = self.nodes
        leader_prefix = LogEntry(1, 2, f"leader-prefix-{self.seed}")
        follower_prefix = LogEntry(1, 1, f"follower-prefix-{self.seed}")
        suffix = LogEntry(2, 2, f"shared-suffix-{self.seed}")
        self.seed_log(a, 1, leader_prefix.term, leader_prefix.digest)
        self.seed_log(a, 2, suffix.term, suffix.digest)
        self.seed_log(b, 1, follower_prefix.term, follower_prefix.digest)
        self.append(b, a, 2, 1, 2, suffix)

    def minority_commit(self) -> None:
        a, b, c = self.nodes
        first = LogEntry(1, 1, f"minority-{self.seed}")
        replacement = LogEntry(1, 2, f"replacement-{self.seed}")
        self.seed_log(a, 1, first.term, first.digest)
        if self.commit(a, first, [a]):
            self.apply(a, first)
        self.seed_log(b, 1, replacement.term, replacement.digest)
        self.seed_log(c, 1, replacement.term, replacement.digest)
        self.builder.emit(b, "leader_elected", term=2, vote_count=2)
        self.commit(b, replacement, [b, c])
        self.apply(b, replacement)

    def uncommitted_apply(self) -> None:
        a, b, c = self.nodes
        first = LogEntry(1, 1, f"uncommitted-{self.seed}")
        replacement = LogEntry(1, 2, f"committed-later-{self.seed}")
        self.seed_log(a, 1, first.term, first.digest)
        self.apply(a, first)
        self.seed_log(b, 1, replacement.term, replacement.digest)
        self.seed_log(c, 1, replacement.term, replacement.digest)
        self.commit(b, replacement, [b, c])
        self.apply(b, replacement)

    def run(self) -> Trace:
        scenario = getattr(self, self.scenario, None)
        if scenario is None or self.scenario.startswith("_"):
            raise ValueError(f"unknown scenario: {self.scenario}")
        scenario()
        return self.builder.trace()


def run_scenario(
    scenario: str,
    seed: int,
    *,
    enabled_hooks: frozenset[str] = ALL_HOOKS,
    arm: str = "baseline",
    target_hook: str | None = None,
) -> Trace:
    return RaftHarness(scenario, seed, enabled_hooks, arm, target_hook).run()


def run_intervention(hook: str, arm: str, seed: int) -> Trace:
    if hook not in HOOK_SCENARIOS:
        raise ValueError(f"unknown hook: {hook}")
    if arm == "active":
        enabled = ALL_HOOKS - {hook}
    elif arm == "sham":
        enabled = ALL_HOOKS
    else:
        raise ValueError("arm must be active or sham")
    return run_scenario(
        HOOK_SCENARIOS[hook],
        seed,
        enabled_hooks=frozenset(enabled),
        arm=arm,
        target_hook=hook,
    )
