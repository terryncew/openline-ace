#!/usr/bin/env python3
"""Regenerate or check the frozen RCDL-004 learning corpus.

This is the only RCDL-004 file allowed to import the RCDL-003 generator.  The
runtime tournament consumes only the frozen corpus and its digest bindings.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
from pathlib import Path
from typing import Any

from rcdl.canonical import canonical_digest, canonical_json
from rcdl003.contracts import frozen_clauses
from rcdl003.oracle import check_external_behavior
from rcdl003.replica import run_pair
from rcdl003.tournament import held_out_examples

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "relational-contract-discovery-003"
CORPUS = ROOT / "references" / "frozen-learning-corpus.jsonl.gz"
MANIFEST = ROOT / "references" / "frozen-learning-corpus-manifest.json"
SOURCE_COMMIT = "4f7c30e0dd3e1a948c1d97d0153f45d9dde0ff59"
TRAIN_SEEDS = tuple(range(64))
VALIDATION_SEEDS = tuple(range(1_000, 1_016))
DEVELOPMENT_SEEDS = tuple(range(30_000, 30_032))
TEST_SEEDS = tuple(range(90_000, 90_032))
SOURCE_FILES = (
    "rcdl003/contracts.py",
    "rcdl003/oracle.py",
    "rcdl003/replica.py",
    "rcdl003/tournament.py",
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _source_bindings() -> dict[str, Any]:
    clauses = []
    for path in sorted((SOURCE / "clauses").glob("*.json")):
        clauses.append(
            {
                "path": f"clauses/{path.name}",
                "file_sha256": _sha256(path.read_bytes()),
            }
        )
    engine_reference = SOURCE / "references" / "rcdl_0_1_engine_reference.json"
    return {
        "repository_commit": SOURCE_COMMIT,
        "source_experiment": "../relational-contract-discovery-003",
        "source_files": [
            {"path": path, "sha256": _sha256((SOURCE / path).read_bytes())}
            for path in SOURCE_FILES
        ],
        "clauses": clauses,
        "engine_reference": {
            "path": "references/rcdl_0_1_engine_reference.json",
            "sha256": _sha256(engine_reference.read_bytes()),
        },
    }


def _row(split: str, trace_document: dict[str, Any], failed: bool) -> dict[str, Any]:
    example_id = canonical_digest(
        {"split": split, "failed": failed, "trace": trace_document}
    )
    return {
        "schema": "rcdl.learning-example/0.1",
        "example_id": example_id,
        "split": split,
        "failed": failed,
        "trace": trace_document,
    }


def _single_fault_rows(split: str, seeds: tuple[int, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for seed in seeds:
        for clause in frozen_clauses():
            for arm in ("active", "sham"):
                run = run_pair(clause.hook, arm, seed)
                failed = not check_external_behavior(run.outcome).passed
                rows.append(_row(split, run.trace.to_dict(), failed))
    return rows


def build() -> tuple[bytes, dict[str, Any]]:
    rows = _single_fault_rows("train", TRAIN_SEEDS)
    rows.extend(_single_fault_rows("validation", VALIDATION_SEEDS))
    rows.extend(
        _row("test", example.trace.to_dict(), example.failed)
        for example in held_out_examples(TEST_SEEDS)
    )
    order = {"train": 0, "validation": 1, "test": 2}
    rows.sort(key=lambda item: (order[item["split"]], item["example_id"]))
    payload = b"".join(canonical_json(row) + b"\n" for row in rows)
    compressed = gzip.compress(payload, compresslevel=9, mtime=0)
    splits = {name: sum(row["split"] == name for row in rows) for name in order}
    manifest = {
        "schema": "rcdl.frozen-learning-corpus/0.1",
        "generator": {
            "training_seeds": list(TRAIN_SEEDS),
            "validation_seeds": list(VALIDATION_SEEDS),
            "test_seeds": list(TEST_SEEDS),
            "training_perturbations": "single_fault_active_and_sham",
            "test_perturbations": "held_out_multi_fault_active_and_sham",
            "test_representation_variants": 5,
            "development_disclosure": {
                "model_design_observed_seeds": list(DEVELOPMENT_SEEDS),
                "excluded_from_final_scoring": True,
                "final_audit_seeds_selected_after_model_freeze": True,
            },
        },
        "compressed_sha256": _sha256(compressed),
        "payload_sha256": _sha256(payload),
        "row_count": len(rows),
        "splits": splits,
        "label_boundary": {
            "labels_available_during_training": True,
            "labels_unavailable_at_prediction": True,
            "intervention_labels_in_trace": False,
            "oracle_values_in_trace": False,
            "raw_identity_values_allowed_as_features": False,
        },
        "source_bindings": _source_bindings(),
    }
    return compressed, manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    compressed, manifest = build()
    manifest_payload = canonical_json(manifest) + b"\n"
    if args.check:
        if not CORPUS.is_file() or CORPUS.read_bytes() != compressed:
            raise SystemExit("frozen corpus differs from deterministic regeneration")
        if not MANIFEST.is_file() or MANIFEST.read_bytes() != manifest_payload:
            raise SystemExit("frozen corpus manifest differs from regeneration")
        print(canonical_json({"verified": True, "rows": manifest["row_count"], "payload_sha256": manifest["payload_sha256"]}).decode())
        return 0
    CORPUS.parent.mkdir(parents=True, exist_ok=True)
    CORPUS.write_bytes(compressed)
    MANIFEST.write_bytes(manifest_payload)
    print(canonical_json({"written": True, "rows": manifest["row_count"], "payload_sha256": manifest["payload_sha256"]}).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
