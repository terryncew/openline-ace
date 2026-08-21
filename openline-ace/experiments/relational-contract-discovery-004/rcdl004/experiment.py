"""Run and freeze the RCDL-004 learned-baseline pressure test."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

from rcdl.canonical import canonical_digest, canonical_json

from . import __version__
from .manifest import write_bound_json
from .projection import build_projection, write_projection
from .tournament import run_tournament


def _prepare_output(path: Path, force: bool) -> None:
    if path.exists() and any(path.iterdir()):
        if not force:
            raise FileExistsError(f"output directory is not empty: {path}")
        for child in path.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    path.mkdir(parents=True, exist_ok=True)


def run_experiment(output: str | Path, *, force: bool = False) -> dict[str, Any]:
    output_path = Path(output)
    _prepare_output(output_path, force)
    tournament, prediction_rows = run_tournament()
    prediction_path = output_path / "predictions.jsonl"
    prediction_payload = b"".join(canonical_json(row) + b"\n" for row in prediction_rows)
    prediction_path.write_bytes(prediction_payload)
    prediction_digest = hashlib.sha256(prediction_payload).hexdigest()
    scientific = tournament["scientific_verdict"]
    claim_effect = (
        "PREDICTIVE_SUPERIORITY_FALSIFIED_WITHIN_TOURNAMENT"
        if scientific in {"LEARNED_PARITY", "LEARNED_STRICT_WIN"}
        else "BOUNDED_PREDICTIVE_ADVANTAGE_SUPPORTED"
        if scientific == "RCDL_STRICT_WIN"
        else "PREDICTIVE_COMPARISON_UNDECIDABLE"
    )
    pressure_test_id = canonical_digest(
        {
            "tool_version": __version__,
            "corpus_payload_sha256": tournament["corpus"]["payload_sha256"],
            "feature_schema_digest": tournament["feature_schema_digest"],
            "prediction_sha256": prediction_digest,
        }
    )
    manifest = {
        "schema": "rcdl.learned-pressure-test-manifest/0.4",
        "tool_version": __version__,
        "experiment_id": "relational-contract-discovery-004",
        "pressure_test_id": pressure_test_id,
        "ace": {
            "level": "1_CANDIDATE",
            "promotion_authorized": False,
            "receipt_gate_authorization": "NONE",
        },
        "protocol": {
            "status": "VALID_RESULT",
            "development_seeds_excluded": True,
            "final_audit_seed_count": 32,
            "same_builder": True,
            "independent_developer_or_lab": False,
            "stochastic_samples": False,
        },
        "tournament": tournament,
        "predictions": {
            "path": prediction_path.name,
            "sha256": prediction_digest,
            "row_count": len(prediction_rows),
            "schema": "rcdl.pressure-test-prediction/0.1",
        },
        "claim_effect": claim_effect,
        "limitations": [
            "The rule-set design was developed by the same builder after observing an excluded development split.",
            "Fresh audit seeds change opaque identities but not the deterministic perturbation semantics.",
            "The learned models are bounded deterministic trees, a margin model, and a relational DNF; no neural model is tested.",
            "Predictive parity does not reproduce RCDL's intervention evidence or causal standing.",
            "No independent team, stochastic LLM, token shock, timing shock, or semantic-shock transport is tested.",
            "The clause vocabulary and task-bag aggregation remain domain supplied.",
            "The projection grants no policy authority.",
        ],
        "verdict": f"PRESSURE_TEST_VALID_{scientific}",
    }
    manifest_path = output_path / "pressure-test-manifest.json"
    manifest_digest = write_bound_json(manifest, manifest_path)
    projection = build_projection(manifest, manifest_digest)
    projection_path = output_path / "contract-projection.json"
    projection_digest = write_projection(projection, projection_path)
    summary = {
        "schema": "rcdl.learned-pressure-test-summary/0.4",
        "verdict": manifest["verdict"],
        "scientific_verdict": scientific,
        "claim_effect": claim_effect,
        "manifest": manifest_path.name,
        "manifest_digest": manifest_digest,
        "projection": projection_path.name,
        "projection_digest": projection_digest,
        "predictions": prediction_path.name,
        "prediction_digest": prediction_digest,
        "test_examples": len(prediction_rows),
        "best_learned_model": tournament["best_learned_model"],
        "rcdl_balanced_accuracy_ppm": tournament["rcdl_contract_predictor"]["test_score"]["balanced_accuracy_ppm"],
        "best_learned_balanced_accuracy_ppm": tournament["best_learned_score"]["balanced_accuracy_ppm"],
        "promotion_authorized": False,
    }
    (output_path / "summary.json").write_bytes(canonical_json(summary) + b"\n")
    return summary

