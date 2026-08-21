"""Materialize canonical RCDL-005 tournament evidence."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

from . import __version__
from .canonical import canonical_digest, canonical_json
from .tournament import run_tournament


def _prepare(path: Path, force: bool) -> None:
    if path.exists() and any(path.iterdir()):
        if not force:
            raise FileExistsError(f"output directory is not empty: {path}")
        for child in path.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    path.mkdir(parents=True, exist_ok=True)


def _write(document: dict[str, Any], path: Path, sidecar: bool = False) -> str:
    payload = canonical_json(document) + b"\n"
    path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    if sidecar:
        path.with_suffix(path.suffix + ".sha256").write_text(
            f"{digest}  {path.name}\n", encoding="utf-8"
        )
    return digest


def run_experiment(output: str | Path, *, force: bool = False) -> dict[str, Any]:
    output_path = Path(output)
    _prepare(output_path, force)
    tournament, records = run_tournament()
    records_payload = b"".join(canonical_json(record) + b"\n" for record in records)
    records_path = output_path / "causal-utility-results.jsonl"
    records_path.write_bytes(records_payload)
    records_digest = hashlib.sha256(records_payload).hexdigest()
    verdict = tournament["scientific_verdict"]
    claim_effect = {
        "CAUSAL_UTILITY_PARITY": "UNIQUE_CAUSAL_UTILITY_FALSIFIED_WITHIN_TOURNAMENT",
        "LEARNED_STRICT_UTILITY_WIN": "RCDL_CAUSAL_UTILITY_ADVANTAGE_FALSIFIED_WITHIN_TOURNAMENT",
        "RCDL_STRICT_UTILITY_WIN": "BOUNDED_RCDL_CAUSAL_UTILITY_ADVANTAGE_SUPPORTED",
        "MIXED_CAUSAL_UTILITY": "CAUSAL_UTILITY_COMPARISON_UNDECIDABLE",
        "INVALID_TOURNAMENT": "NO_SCIENTIFIC_RESULT",
    }[verdict]
    manifest = {
        "schema": "rcdl.causal-utility-manifest/0.5",
        "tool_version": __version__,
        "experiment_id": "relational-contract-discovery-005",
        "tournament_id": canonical_digest(
            {
                "version": __version__,
                "records_sha256": records_digest,
                "verdict": verdict,
            }
        ),
        "ace": {
            "level": "1_CANDIDATE",
            "promotion_authorized": False,
            "receipt_gate_authorization": "NONE",
        },
        "tournament": tournament,
        "results": {
            "path": records_path.name,
            "sha256": records_digest,
            "row_count": len(records),
            "schema": "rcdl.causal-utility-result/0.5",
        },
        "claim_effect": claim_effect,
        "limitations": [
            "Both policies and the benchmark were implemented by the same builder.",
            "The learned policy is trained on action-complete deterministic historical signatures.",
            "The symbolic policy receives a bounded, domain-supplied contract grammar.",
            "The two execution adapters share one official behavioral oracle.",
            "The declared perturbation regime excludes interventions that break three or four relations.",
            "The benchmark contains no stochastic LLM, timing, token, prompt, or tool transport.",
            "No independent developer, laboratory, or external replication is represented.",
            "The projection grants no enforcement or promotion authority.",
        ],
        "verdict": f"CAUSAL_UTILITY_TEST_{verdict}",
    }
    manifest_path = output_path / "causal-utility-manifest.json"
    manifest_digest = _write(manifest, manifest_path, sidecar=True)
    projection = {
        "schema": "openline.verified-handoff-projection/0.5",
        "projection_id": canonical_digest(
            {"manifest_sha256": manifest_digest, "claim_effect": claim_effect}
        ),
        "source": {
            "experiment": "relational-contract-discovery-005",
            "manifest": manifest_path.name,
            "manifest_sha256": manifest_digest,
            "results_sha256": records_digest,
        },
        "claim": {
            "effect": claim_effect,
            "scientific_verdict": verdict,
            "scope": "frozen deterministic equal-budget causal-utility tournament only",
        },
        "gate": {
            "verified": tournament["protocol_status"] == "VALID_RESULT",
            "policy_authority": "NONE",
            "promotion_authorized": False,
        },
        "reopen_if": [
            "an independent implementation produces a non-parity result",
            "a learned active policy fails under a genuinely held-out causal mechanism",
            "transport is tested on stochastic multi-agent workflows",
        ],
    }
    projection_path = output_path / "verified-handoff-projection.json"
    projection_digest = _write(projection, projection_path, sidecar=True)
    summary = {
        "schema": "rcdl.causal-utility-summary/0.5",
        "verdict": manifest["verdict"],
        "scientific_verdict": verdict,
        "claim_effect": claim_effect,
        "manifest": manifest_path.name,
        "manifest_digest": manifest_digest,
        "projection": projection_path.name,
        "projection_digest": projection_digest,
        "results": records_path.name,
        "results_digest": records_digest,
        "result_rows": len(records),
        "promotion_authorized": False,
    }
    _write(summary, output_path / "summary.json")
    return summary

