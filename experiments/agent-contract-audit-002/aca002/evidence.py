from __future__ import annotations

import json
from pathlib import Path

from .canonical import file_sha256, write_json
from .compiler import compile_candidates
from .fixture import conformance_results
from .grade import grade_external
from .ingest import verify_against_schedule
from .pin import verify_a001_pin
from .replay import replay_verifier

PROPOSED = [
    {
      "candidate_id": "candidate-ticket-value-binding",
      "text": "Successful completion depends on the ticket value being bound to the current task state.",
      "scope": "ticket relay workflow",
      "relation": "freshness/provenance",
      "evidence_refs": ["baseline:read_ticket.value"]
    },
    {
      "candidate_id": "candidate-audit-marker",
      "text": "Successful completion depends on the stable audit marker remaining present.",
      "scope": "ticket relay workflow",
      "relation": "presence/order ritual candidate",
      "evidence_refs": ["baseline:read_ticket.marker"]
    }
]
MAPPINGS = [
    {"candidate_id":"candidate-ticket-value-binding","surface_id":"ticket.token_freshness"},
    {"candidate_id":"candidate-audit-marker","surface_id":"ticket.audit_marker_presence"}
]

EVIDENCE_FILES = (
    "candidates.json", "results.jsonl", "grade.json", "independent-replay.json",
    "protocol-manifest.json", "verified-handoff-projection.json", "experiment-receipt.json",
    "verdict.json"
)


def build_conformance(root: Path, output: Path) -> dict:
    pins = verify_a001_pin()
    catalog = json.loads((root / "fixtures" / "surface_catalog.json").read_text())
    tasks_doc = json.loads((root / "fixtures" / "tasks.json").read_text())
    candidates = compile_candidates(PROPOSED, MAPPINGS, catalog)
    schedule, rows = conformance_results(candidates, tasks_doc["tasks"])
    verify_against_schedule(rows, schedule)
    replay = replay_verifier(rows, tasks_doc["tasks"])
    if not replay["verified"]:
        raise RuntimeError("independent verifier replay failed")
    grade = grade_external(candidates, rows)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "candidates.json", candidates)
    with (output / "results.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    write_json(output / "grade.json", grade)
    write_json(output / "independent-replay.json", replay)
    manifest = {
        "protocol": "openline.agent-contract-audit.protocol-manifest.v1",
        "experiment": "agent-contract-audit-002",
        "base_commit": "b0c93bb2f751025b0e8b804ee26700e0c2ad2a9e",
        "a001_git_blob_pins": pins,
        "rows": len(rows),
        "pairs_per_candidate": 64,
        "provider": {"kind": "fixture", "external": False},
        "authority": "NONE",
        "grade_sha256": file_sha256(output / "grade.json"),
        "results_sha256": file_sha256(output / "results.jsonl"),
        "replay_sha256": file_sha256(output / "independent-replay.json"),
    }
    write_json(output / "protocol-manifest.json", manifest)
    projection = {
        "claim": "A-002 protocol mechanics are closed and ready for a blind external stochastic run.",
        "external_claim_earned": False,
        "scientific_standing": "MECHANICS_ONLY_NOT_EXTERNAL_AGENT_EVIDENCE",
        "manifest_sha256": file_sha256(output / "protocol-manifest.json"),
        "policy_authority": "NONE",
    }
    write_json(output / "verified-handoff-projection.json", projection)
    receipt = {
        "status": "COMMIT",
        "commit_scope": "protocol-conformance-artifact-only",
        "external_agent_evidence": False,
        "authority": "NONE",
        "manifest_sha256": file_sha256(output / "protocol-manifest.json"),
        "projection_sha256": file_sha256(output / "verified-handoff-projection.json"),
    }
    write_json(output / "experiment-receipt.json", receipt)
    verdict = {
        "verdict": "PROTOCOL_CONFORMANCE_PASS_EXTERNAL_UNRUN",
        "scientific_standing": "MECHANICS_ONLY_NOT_EXTERNAL_AGENT_EVIDENCE",
        "authority": "NONE",
        "supported": grade["supported"],
        "rejected_rituals": grade["rejected_rituals"],
        "external_provider_run": False,
        "receipt_sha256": file_sha256(output / "experiment-receipt.json"),
    }
    write_json(output / "verdict.json", verdict)
    index = {}
    for name in EVIDENCE_FILES:
        p = output / name
        index[name] = {"sha256": file_sha256(p), "size": p.stat().st_size}
    write_json(output / "evidence-index.json", index)
    return verdict


def verify_evidence(output: Path) -> dict:
    index = json.loads((output / "evidence-index.json").read_text())
    if set(index) != set(EVIDENCE_FILES):
        raise RuntimeError("evidence index is not closed")
    for name, meta in index.items():
        p = output / name
        if not p.exists() or p.stat().st_size != meta["size"] or file_sha256(p) != meta["sha256"]:
            raise RuntimeError(f"evidence mismatch: {name}")
    manifest = json.loads((output / "protocol-manifest.json").read_text())
    if manifest["results_sha256"] != file_sha256(output / "results.jsonl"):
        raise RuntimeError("manifest does not bind results")
    projection = json.loads((output / "verified-handoff-projection.json").read_text())
    if projection["manifest_sha256"] != file_sha256(output / "protocol-manifest.json"):
        raise RuntimeError("projection does not bind manifest")
    receipt = json.loads((output / "experiment-receipt.json").read_text())
    if receipt["projection_sha256"] != file_sha256(output / "verified-handoff-projection.json"):
        raise RuntimeError("receipt does not bind projection")
    return json.loads((output / "verdict.json").read_text())
