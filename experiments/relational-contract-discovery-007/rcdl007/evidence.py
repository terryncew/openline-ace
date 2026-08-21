from __future__ import annotations

import json
from pathlib import Path

from .canonical import file_digest, write_json
from .policies import policy_boundary
from .tournament import run_tournament


EVIDENCE_FILES = (
    "evaluation-results.jsonl",
    "pre-adjudication-manifest.json",
    "verified-handoff-projection.json",
    "experiment-receipt.json",
)


def build_evidence(output: Path, identities: int = 16) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    result = run_tournament(identities)
    rows_path = output / "evaluation-results.jsonl"
    rows_path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in result["rows"]),
        encoding="utf-8",
    )
    manifest = {
        "authority": "NONE",
        "budget": result["budget"],
        "claim_effect": result["claim_effect"],
        "evaluation_families": result["evaluation_families"],
        "identities_per_family": result["identities_per_family"],
        "metrics": result["metrics"],
        "policy_boundary": policy_boundary(),
        "results_sha256": file_digest(rows_path),
        "transport_failures": result["transport_failures"],
        "verdict": result["verdict"],
    }
    manifest_path = output / "pre-adjudication-manifest.json"
    write_json(manifest_path, manifest)
    projection = {
        "claim": "Explicit relational hypotheses provide unique pre-adjudication causal-search utility under equal budgets.",
        "claim_effect": result["claim_effect"],
        "manifest_sha256": file_digest(manifest_path),
        "policy_authority": "NONE",
        "verdict": result["verdict"],
    }
    projection_path = output / "verified-handoff-projection.json"
    write_json(projection_path, projection)
    receipt = {
        "authority": "NONE",
        "manifest_sha256": file_digest(manifest_path),
        "projection_sha256": file_digest(projection_path),
        "results_sha256": file_digest(rows_path),
        "status": "COMMIT",
        "verdict": result["verdict"],
    }
    receipt_path = output / "experiment-receipt.json"
    write_json(receipt_path, receipt)
    index = {
        name: {"sha256": file_digest(output / name), "size": (output / name).stat().st_size}
        for name in EVIDENCE_FILES
    }
    write_json(output / "evidence-index.json", index)
    return {"verdict": result["verdict"], "manifest": manifest}


def verify_evidence(output: Path) -> None:
    index_path = output / "evidence-index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if set(index) != set(EVIDENCE_FILES):
        raise RuntimeError("evidence index is not closed")
    for name, metadata in index.items():
        path = output / name
        if not path.exists():
            raise RuntimeError(f"missing evidence file: {name}")
        if path.stat().st_size != metadata["size"] or file_digest(path) != metadata["sha256"]:
            raise RuntimeError(f"evidence mismatch: {name}")
    manifest = json.loads((output / "pre-adjudication-manifest.json").read_text(encoding="utf-8"))
    if manifest["results_sha256"] != file_digest(output / "evaluation-results.jsonl"):
        raise RuntimeError("manifest does not bind results")
    projection = json.loads((output / "verified-handoff-projection.json").read_text(encoding="utf-8"))
    if projection["manifest_sha256"] != file_digest(output / "pre-adjudication-manifest.json"):
        raise RuntimeError("projection does not bind manifest")
    receipt = json.loads((output / "experiment-receipt.json").read_text(encoding="utf-8"))
    if receipt["projection_sha256"] != file_digest(output / "verified-handoff-projection.json"):
        raise RuntimeError("receipt does not bind projection")
