from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .blind import make_compiler_packet, make_proposer_packet
from .canonical import file_sha256, write_json
from .compiler import compile_candidates
from .grade import grade_external
from .ingest import verify_against_schedule
from .live import run_openai_request
from .manifests import contract_manifests
from .replay import replay_verifier
from .schedule import build_schedule


def _extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


def _llm_json(model_name: str, instructions: str, payload: dict[str, Any]) -> Any:
    try:
        from agents import Agent, Runner
    except Exception as exc:
        raise RuntimeError("install openai-agents>=0.17.6,<0.18") from exc
    agent = Agent(
        name="Untrusted audit proposer",
        model=model_name,
        instructions=instructions + " Return strict JSON only.",
    )
    result = Runner.run_sync(agent, json.dumps(payload, sort_keys=True), max_turns=3)
    return _extract_json(str(result.final_output))


def run_live(root: Path, output: Path, *, model_name: str, pairs: int = 64, baseline_runs: int = 8) -> dict[str, Any]:
    tasks_doc = json.loads((root / "fixtures" / "tasks.json").read_text())
    catalog = json.loads((root / "fixtures" / "surface_catalog.json").read_text())
    tasks = tasks_doc["tasks"]
    output.mkdir(parents=True, exist_ok=True)

    # Baseline traces are generated first and sealed before proposer/arm execution.
    baseline_traces = []
    for i in range(baseline_runs):
        task = tasks[i % len(tasks)]
        req = {
            "candidate_id": "baseline-observation",
            "surface_id": "none",
            "pair_id": f"baseline:{i:04d}",
            "task_id": task["task_id"],
            "seed": 810000 + i,
            "arm": "baseline",
            "intervention": {"op": "none"},
        }
        row = run_openai_request(req, task, model_name)
        # Public trace projection contains no hidden task token labels beyond what the agent observed.
        from .task import observation_for
        baseline_traces.append({
            "trace_id": row["trace_sha256"],
            "task_id": task["task_id"],
            "events": ["read_ticket", "final_output"],
            "tool_observation": observation_for(task, "none"),
            "final_success": row["verifier"]["success"],
        })
    proposer_packet = make_proposer_packet([t for t in baseline_traces if t["final_success"]])
    write_json(output / "proposer-packet.json", proposer_packet)
    write_json(output / "baseline-seal.json", {
        "protocol": "openline.agent-contract-audit.baseline-seal.v1",
        "proposer_packet_sha256": file_sha256(output / "proposer-packet.json"),
        "model_requested": model_name,
        "baseline_runs": baseline_runs,
        "authority": "NONE",
    })
    proposal_raw = _llm_json(
        model_name,
        "You propose candidate workflow dependencies but have no authority. Output a JSON array of objects with candidate_id, text, scope, relation, evidence_refs.",
        proposer_packet,
    )
    if not isinstance(proposal_raw, list):
        raise RuntimeError("proposer did not return a candidate array")
    write_json(output / "proposer-output.json", proposal_raw)

    compiler_packet = make_compiler_packet(proposal_raw, catalog)
    write_json(output / "compiler-packet.json", compiler_packet)
    mapping_raw = _llm_json(
        model_name,
        "You map candidates to public intervention surfaces but do not decide whether they are necessary. Output a JSON array of {candidate_id,surface_id}.",
        compiler_packet,
    )
    if not isinstance(mapping_raw, list):
        raise RuntimeError("compiler did not return a mapping array")
    write_json(output / "compiler-output.json", mapping_raw)
    candidates = compile_candidates(proposal_raw, mapping_raw, catalog)[:3]
    if len(candidates) < 2:
        write_json(output / "live-verdict.json", {
            "verdict": "PROPOSER_COVERAGE_FAILURE",
            "authority": "NONE",
            "candidate_count": len(candidates),
        })
        return {"verdict": "PROPOSER_COVERAGE_FAILURE"}
    write_json(output / "compiled-candidates.json", candidates)

    schedule = build_schedule(candidates, tasks, pairs=pairs)
    with (output / "schedule.jsonl").open("w", encoding="utf-8") as f:
        for row in schedule:
            f.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    write_json(output / "pre-intervention-seal.json", {
        "protocol": "openline.agent-contract-audit.pre-intervention-seal.v1",
        "baseline_seal_sha256": file_sha256(output / "baseline-seal.json"),
        "proposer_output_sha256": file_sha256(output / "proposer-output.json"),
        "compiler_packet_sha256": file_sha256(output / "compiler-packet.json"),
        "compiler_output_sha256": file_sha256(output / "compiler-output.json"),
        "compiled_candidates_sha256": file_sha256(output / "compiled-candidates.json"),
        "schedule_sha256": file_sha256(output / "schedule.jsonl"),
        "surface_catalog_sha256": file_sha256(root / "fixtures" / "surface_catalog.json"),
        "tasks_sha256": file_sha256(root / "fixtures" / "tasks.json"),
        "authority": "NONE",
    })
    results = []
    by_task = {t["task_id"]: t for t in tasks}
    for request in schedule:
        results.append(run_openai_request(request, by_task[request["task_id"]], model_name))
    verify_against_schedule(results, schedule)
    with (output / "external-results.jsonl").open("w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")

    replay = replay_verifier(results, tasks)
    write_json(output / "independent-replay.json", replay)
    if not replay["verified"]:
        raise RuntimeError("external verifier replay failed")
    grade = grade_external(candidates, results)
    write_json(output / "grade.json", grade)

    supported_surfaces = {g["surface_id"] for g in grade["grades"] if g["standing"] == "SUPPORTED"}
    rejected_surfaces = {g["surface_id"] for g in grade["grades"] if g["standing"] == "REJECTED_RITUAL"}
    separation = "ticket.token_freshness" in supported_surfaces and bool(
        rejected_surfaces & {"ticket.audit_marker_presence", "ticket.padding_presence"}
    )
    verdict = {
        "verdict": "BLIND_EXTERNAL_SEPARATION" if separation else "BLIND_EXTERNAL_SEPARATION_NOT_EARNED",
        "authority": "NONE",
        "provider": {"kind": "openai-agents-sdk", "model": model_name, "external": True},
        "supported_surfaces": sorted(supported_surfaces),
        "rejected_ritual_surfaces": sorted(rejected_surfaces),
        "proposer_packet_sha256": file_sha256(output / "proposer-packet.json"),
        "compiler_packet_sha256": file_sha256(output / "compiler-packet.json"),
        "pre_intervention_seal_sha256": file_sha256(output / "pre-intervention-seal.json"),
    }
    write_json(output / "live-verdict.json", verdict)
    write_json(output / "contract-manifests.json", contract_manifests(candidates, grade, provider_verified=True))
    return verdict
