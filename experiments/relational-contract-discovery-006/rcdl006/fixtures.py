"""Fail-closed loaders for the preregistered proposal and oracle fixtures."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import canonical_digest, load_json
from .environment import (
    ALL_OPERATORS,
    MANUFACTURED_OPERATORS,
    NATIVE_OPERATORS,
    NUISANCE_OPERATORS,
)
from .model import CLAUSE_ID, Proposal, Split, Standing, Task


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class OracleEntry:
    proposal_id: str
    standing: Standing


@dataclass(frozen=True)
class FrozenFixtures:
    config: dict[str, Any]
    proposals: tuple[Proposal, ...]
    oracle: dict[str, OracleEntry]

    def by_split(self, split: Split) -> tuple[Proposal, ...]:
        return tuple(item for item in self.proposals if item.split is split)


def proposal_digest(record: dict[str, Any]) -> str:
    body = {key: value for key, value in record.items() if key != "proposal_digest"}
    return canonical_digest(body)


def load_fixtures(root: str | Path = EXPERIMENT_ROOT) -> FrozenFixtures:
    root_path = Path(root)
    config = load_json(root_path / "experiment_config.json")
    proposal_doc = load_json(root_path / "references" / "frozen-proposals.json")
    oracle_doc = load_json(root_path / "references" / "official-oracle-model.json")
    if not isinstance(config, dict) or config.get("schema") != "rcdl.envharness-heldout-config/0.6":
        raise ValueError("experiment config boundary failed")
    if config.get("authority") != "NONE" or config.get("clause_id") != CLAUSE_ID:
        raise ValueError("experiment authority boundary failed")
    if config.get("budgets") != {"queries_per_case": 3, "symbolic": 3, "learned": 3}:
        raise ValueError("equal intervention budget boundary failed")
    if not isinstance(proposal_doc, dict) or set(proposal_doc) != {"schema", "proposals"}:
        raise ValueError("proposal document closure failed")
    if proposal_doc["schema"] != "rcdl.untrusted-proposal-set/0.6":
        raise ValueError("proposal schema failed")
    raw_proposals = proposal_doc["proposals"]
    if not isinstance(raw_proposals, list) or len(raw_proposals) != 12:
        raise ValueError("proposal cardinality failed")
    allowed_keys = {
        "active_energy", "candidate_clause", "layers", "proposal_digest",
        "proposal_id", "sham_energy", "split",
    }
    proposals: list[Proposal] = []
    for record in raw_proposals:
        if not isinstance(record, dict) or set(record) != allowed_keys:
            raise ValueError("proposal record closure failed")
        if record["proposal_digest"] != proposal_digest(record):
            raise ValueError(f"proposal digest mismatch: {record.get('proposal_id')}")
        proposal = Proposal.from_dict(record)
        if not proposal.layers or not set(proposal.layers).issubset(ALL_OPERATORS):
            raise ValueError("proposal operator boundary failed")
        if proposal.active_energy != proposal.sham_energy:
            raise ValueError("active/sham energy mismatch")
        proposals.append(proposal)
    if len({item.proposal_id for item in proposals}) != len(proposals):
        raise ValueError("duplicate proposal id")
    development = tuple(item for item in proposals if item.split is Split.DEVELOPMENT)
    evaluation = tuple(item for item in proposals if item.split is Split.EVALUATION)
    if len(development) != 6 or len(evaluation) != 6:
        raise ValueError("split size boundary failed")
    if any(len(item.layers) != 1 for item in development) or any(len(item.layers) != 2 for item in evaluation):
        raise ValueError("held-out composition boundary failed")
    dev_operators = {layer for item in development for layer in item.layers}
    eval_operators = {layer for item in evaluation for layer in item.layers}
    if dev_operators & eval_operators:
        raise ValueError("mechanism operator leakage")
    if not isinstance(oracle_doc, dict) or set(oracle_doc) != {"schema", "oracle", "entries"}:
        raise ValueError("oracle document closure failed")
    if oracle_doc["schema"] != "rcdl.official-oracle-model/0.6" or oracle_doc["oracle"] != "original-code-repair-verifier":
        raise ValueError("original verifier boundary failed")
    entries = oracle_doc["entries"]
    if not isinstance(entries, list) or len(entries) != len(proposals):
        raise ValueError("oracle cardinality failed")
    oracle: dict[str, OracleEntry] = {}
    for item in entries:
        if not isinstance(item, dict) or set(item) != {"proposal_id", "standing"}:
            raise ValueError("oracle entry closure failed")
        entry = OracleEntry(str(item["proposal_id"]), Standing(item["standing"]))
        if entry.proposal_id in oracle:
            raise ValueError("oracle entry failed")
        oracle[entry.proposal_id] = entry
    if set(oracle) != {item.proposal_id for item in proposals}:
        raise ValueError("oracle/proposal identity mismatch")
    for proposal in proposals:
        entry = oracle[proposal.proposal_id]
        core = set(proposal.layers)
        expected = (
            Standing.SUPPORTED_NATIVE if core & NATIVE_OPERATORS else
            Standing.REJECTED_IMPOSED if core & MANUFACTURED_OPERATORS else
            Standing.REJECTED_NUISANCE
        )
        if entry.standing is not expected:
            raise ValueError("official oracle inconsistency")
    return FrozenFixtures(config=config, proposals=tuple(proposals), oracle=oracle)


def heldout_tasks(count: int = 16) -> tuple[Task, ...]:
    if count != 16:
        raise ValueError("held-out task count is frozen at 16")
    return tuple(
        Task(
            task_id=f"heldout-{index:02d}",
            correct_patch=f"patch-correct-{(index * 17 + 5) % 97:02d}",
            alternate_patch=f"patch-alternate-{(index * 29 + 11) % 97:02d}",
            nuisance_seed=index * 7919 + 23,
        )
        for index in range(count)
    )


def development_tasks() -> tuple[Task, ...]:
    return tuple(
        Task(
            task_id=f"development-{index:02d}",
            correct_patch=f"dev-correct-{index}",
            alternate_patch=f"dev-alternate-{index}",
            nuisance_seed=101 + index,
        )
        for index in range(3)
    )
