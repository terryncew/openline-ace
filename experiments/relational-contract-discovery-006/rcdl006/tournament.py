"""Run the frozen held-out EnvHarness mechanism tournament."""

from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

from .canonical import canonical_digest, canonical_json, write_canonical
from .execution import execute_queries
from .fixtures import EXPERIMENT_ROOT, development_tasks, heldout_tasks, load_fixtures
from .model import PolicyDecision, Proposal, QueryTranscript, Split, Standing
from .policies import policy_boundary, symbolic_decision, train_learned_policy
from .upstream import verify_upstream


RESULT_SCHEMA = "rcdl.envharness-heldout-result/0.6"
MANIFEST_SCHEMA = "rcdl.envharness-heldout-manifest/0.6"
PROJECTION_SCHEMA = "openline.verified-handoff-projection/0.6"
SCIENTIFIC_VERDICT = "HELD_OUT_MECHANISM_CAUSAL_PARITY"
CLAIM_EFFECT = "NATIVE_VS_IMPOSED_DISTINCTION_SUPPORTED_UNIQUE_ADVANTAGE_NOT_FOUND"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record(
    proposal: Proposal,
    task_id: str,
    agent: str,
    policy: str,
    transcript: QueryTranscript,
    decision: PolicyDecision,
    expected: Standing,
) -> dict[str, Any]:
    return {
        "agent_implementation": agent,
        "correct_recovery_horizon": decision.predicted_recovery_horizon
        == int(transcript.restoration.recovery_horizon or 0),
        "correct_standing": decision.standing is expected,
        "decision": decision.to_dict(),
        "expected_standing": expected.value,
        "policy": policy,
        "proposal_digest": proposal.proposal_digest,
        "proposal_id": proposal.proposal_id,
        "query_transcript": transcript.to_dict(),
        "schema": RESULT_SCHEMA,
        "split": proposal.split.value,
        "task_id": task_id,
    }


def _transport_ok(records: list[dict[str, Any]]) -> bool:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for record in records:
        groups.setdefault(
            (record["task_id"], record["proposal_id"], record["policy"]), []
        ).append(record)
    if any({item["agent_implementation"] for item in group} != {"ledger-v2", "queue-v2"} for group in groups.values()):
        return False
    return all(
        len(
            {
                (
                    item["decision"]["standing"],
                    item["decision"]["predicted_recovery_horizon"],
                    canonical_digest(item["query_transcript"]),
                )
                for item in group
            }
        )
        == 1
        for group in groups.values()
    )


def _metrics(records: list[dict[str, Any]], policy: str) -> dict[str, Any]:
    selected = [item for item in records if item["policy"] == policy]
    correct = sum(bool(item["correct_standing"]) for item in selected)
    recovery = sum(bool(item["correct_recovery_horizon"]) for item in selected)
    counts = Counter(item["decision"]["standing"] for item in selected)
    return {
        "accuracy_ppm": correct * 1_000_000 // len(selected),
        "correct_recovery_horizons": recovery,
        "correct_standings": correct,
        "decision_counts": dict(sorted(counts.items())),
        "policy": policy,
        "runs": len(selected),
    }


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> str:
    payload = b"".join(canonical_json(record) + b"\n" for record in records)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def _prepare_output(output: Path, force: bool) -> None:
    if output.exists() and any(output.iterdir()) and not force:
        raise ValueError("output directory is not empty; pass --force to replace generated files")
    output.mkdir(parents=True, exist_ok=True)
    if force:
        for name in (
            "heldout-mechanism-results.jsonl",
            "heldout-mechanism-manifest.json",
            "heldout-mechanism-manifest.json.sha256",
            "verified-handoff-projection.json",
            "verified-handoff-projection.json.sha256",
            "summary.json",
        ):
            target = output / name
            if target.is_file():
                target.unlink()


def run_tournament(output: str | Path, *, force: bool = False) -> dict[str, Any]:
    destination = Path(output)
    _prepare_output(destination, force)
    fixtures = load_fixtures()
    upstream = verify_upstream()
    dev_examples: list[tuple[QueryTranscript, Standing]] = []
    for proposal in fixtures.by_split(Split.DEVELOPMENT):
        oracle = fixtures.oracle[proposal.proposal_id]
        for task in development_tasks():
            transcript = execute_queries(proposal, task, "direct-v1")
            dev_examples.append((transcript, oracle.standing))
    learned = train_learned_policy(dev_examples)
    records: list[dict[str, Any]] = []
    for task in heldout_tasks(fixtures.config["heldout_tasks"]):
        for proposal in fixtures.by_split(Split.EVALUATION):
            oracle = fixtures.oracle[proposal.proposal_id]
            for agent in fixtures.config["agent_implementations"]["evaluation"]:
                transcript = execute_queries(proposal, task, agent)
                records.append(
                    _record(
                        proposal, task.task_id, agent, "symbolic-rcdl", transcript,
                        symbolic_decision(transcript), oracle.standing,
                    )
                )
                records.append(
                    _record(
                        proposal, task.task_id, agent, learned.name, transcript,
                        learned.decide(transcript), oracle.standing,
                    )
                )
    records.sort(
        key=lambda item: (
            item["task_id"], item["proposal_id"],
            item["agent_implementation"], item["policy"],
        )
    )
    expected_rows = 16 * 6 * 2 * 2
    if len(records) != expected_rows:
        raise RuntimeError("evaluation cardinality failed")
    symbolic = _metrics(records, "symbolic-rcdl")
    baseline = _metrics(records, learned.name)
    sham_failures = sum(
        not item["query_transcript"]["sham"]["external_success"] for item in records
    )
    energy_mismatches = sum(
        item["query_transcript"]["active"]["energy"]
        != item["query_transcript"]["sham"]["energy"]
        for item in records
    )
    transport = _transport_ok(records)
    accuracy_delta = symbolic["accuracy_ppm"] - baseline["accuracy_ppm"]
    valid = (
        symbolic["accuracy_ppm"] == 1_000_000
        and baseline["accuracy_ppm"] == 1_000_000
        and symbolic["correct_recovery_horizons"] == symbolic["runs"]
        and baseline["correct_recovery_horizons"] == baseline["runs"]
        and sham_failures == 0
        and energy_mismatches == 0
        and transport
        and upstream["verified"]
    )
    if not valid:
        raise RuntimeError("frozen validity criteria failed")
    margin = int(fixtures.config["symbolic_advantage_margin_ppm"])
    verdict = (
        "SYMBOLIC_CAUSAL_UTILITY_ADVANTAGE"
        if accuracy_delta >= margin
        else SCIENTIFIC_VERDICT
        if abs(accuracy_delta) < margin
        else "LEARNED_BASELINE_ADVANTAGE"
    )
    results_path = destination / "heldout-mechanism-results.jsonl"
    results_digest = _write_jsonl(results_path, records)
    protocol_digest = canonical_digest(
        {
            "config_sha256": _sha256(EXPERIMENT_ROOT / "experiment_config.json"),
            "oracle_sha256": _sha256(EXPERIMENT_ROOT / "references" / "official-oracle-model.json"),
            "proposals_sha256": _sha256(EXPERIMENT_ROOT / "references" / "frozen-proposals.json"),
            "upstream_commit": upstream["commit"],
        }
    )
    tournament = {
        "accuracy_delta_ppm": accuracy_delta,
        "energy_mismatches": energy_mismatches,
        "heldout_agent_implementations": ["ledger-v2", "queue-v2"],
        "heldout_mechanism_compositions": 6,
        "heldout_tasks": 16,
        "matched_sham_failures": sham_failures,
        "protocol_digest": protocol_digest,
        "protocol_status": "VALID_RESULT",
        "queries_per_case": 3,
        "scientific_verdict": verdict,
        "transport_across_agents": transport,
        "upstream": upstream,
    }
    manifest = {
        "ace": {
            "level": "1_CANDIDATE",
            "promotion_authorized": False,
            "receipt_gate_authorization": "NONE",
        },
        "claim_effect": CLAIM_EFFECT,
        "experiment_id": "relational-contract-discovery-006",
        "limitations": [
            "same-builder deterministic pilot",
            "deterministic EnvRigger-shaped fixtures, not live LLM-generated wrappers",
            "single synthetic code-repair verifier",
            "no independent replication",
            "no stochastic LLM-agent transport",
        ],
        "results": {
            "path": results_path.name,
            "row_count": len(records),
            "schema": RESULT_SCHEMA,
            "sha256": results_digest,
        },
        "schema": MANIFEST_SCHEMA,
        "tool_version": "0.6.0",
        "tournament": tournament,
        "verdict": f"ENVHARNESS_HELDOUT_TEST_{verdict}",
    }
    manifest_path = destination / "heldout-mechanism-manifest.json"
    manifest_digest = write_canonical(manifest_path, manifest)
    manifest_path.with_suffix(".json.sha256").write_text(
        f"{manifest_digest}  {manifest_path.name}\n", encoding="utf-8"
    )
    projection = {
        "claim": {
            "effect": CLAIM_EFFECT,
            "scientific_verdict": verdict,
            "status": "SUPPORTED_WITHIN_FROZEN_PILOT",
        },
        "gate": {
            "policy_authority": "NONE",
            "promotion_authorized": False,
            "verified": True,
        },
        "projection_id": "rcdl-006-envharness-heldout-mechanism",
        "reopen_if": [
            "upstream source pin changes",
            "original verifier changes",
            "held-out mechanism split leaks",
            "matched sham fails",
            "independent or stochastic replication disagrees",
        ],
        "schema": PROJECTION_SCHEMA,
        "source": {
            "experiment": "relational-contract-discovery-006",
            "manifest": manifest_path.name,
            "manifest_sha256": manifest_digest,
            "results_sha256": results_digest,
        },
    }
    projection_path = destination / "verified-handoff-projection.json"
    projection_digest = write_canonical(projection_path, projection)
    projection_path.with_suffix(".json.sha256").write_text(
        f"{projection_digest}  {projection_path.name}\n", encoding="utf-8"
    )
    summary = {
        "baseline": baseline,
        "claim_effect": CLAIM_EFFECT,
        "manifest_digest": manifest_digest,
        "policy_boundary": policy_boundary(),
        "projection_digest": projection_digest,
        "result_rows": len(records),
        "results_digest": results_digest,
        "scientific_verdict": verdict,
        "symbolic": symbolic,
    }
    write_canonical(destination / "summary.json", summary)
    return summary
