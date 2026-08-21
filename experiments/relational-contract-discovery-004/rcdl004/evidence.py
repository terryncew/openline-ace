"""Freeze and verify the bounded RCDL-004 evidence package."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from rcdl.canonical import canonical_digest, canonical_json, load_json_bytes

from .bindings import verify_frozen_bindings
from .manifest import verify_manifest
from .projection import verify_projection

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_SCHEMA = "openline.ace.evidence-index/0.1"
RECEIPT_SCHEMA = "openline.ace.experiment-receipt/0.1"
RECEIPT_CLAIM = (
    "A learned relational rule set matched the frozen RCDL contract predictor "
    "on 1,024 final-audit traces, rejecting unique predictive advantage within "
    "the declared deterministic tournament."
)
RECEIPT_RESULT = "PREDICTIVE_SUPERIORITY_FALSIFIED_WITHIN_TOURNAMENT"


class EvidenceVerificationError(ValueError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_bound_json(document: dict[str, Any], path: Path) -> str:
    payload = canonical_json(document) + b"\n"
    path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return digest


def _verify_bound_json(path: Path) -> tuple[dict[str, Any], str]:
    payload = path.read_bytes()
    document = load_json_bytes(payload)
    if not isinstance(document, dict) or payload != canonical_json(document) + b"\n":
        raise EvidenceVerificationError(f"non-canonical evidence: {path.name}")
    digest = hashlib.sha256(payload).hexdigest()
    sidecar = path.with_suffix(path.suffix + ".sha256")
    parts = sidecar.read_text(encoding="utf-8").strip().split() if sidecar.is_file() else []
    if len(parts) != 2 or parts[0] != digest or parts[1] != path.name:
        raise EvidenceVerificationError(f"evidence sidecar mismatch: {path.name}")
    return document, digest


def _source_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if "evidence" in relative.parts or "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        entries.append(
            {
                "path": relative.as_posix(),
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return entries


def source_tree_digest(root: str | Path = EXPERIMENT_ROOT) -> str:
    return canonical_digest(_source_entries(Path(root)))


def _release_and_summary(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    release = load_json_bytes((root / "evidence" / "release-check.json").read_bytes())
    summary = load_json_bytes((root / "evidence" / "pressure-test" / "summary.json").read_bytes())
    if not isinstance(release, dict) or not isinstance(summary, dict):
        raise EvidenceVerificationError("release or summary evidence is invalid")
    return release, summary


def _validate_release(release: dict[str, Any], summary: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    tests = release.get("unit_tests")
    probe = release.get("randomized_probe")
    replay = release.get("deterministic_replay")
    isolated = release.get("isolated_copy")
    if (
        release.get("verdict") != "PASS"
        or release.get("compileall") != "PASS"
        or not isinstance(tests, dict)
        or tests.get("status") != "PASS"
        or not isinstance(tests.get("test_count"), int)
        or tests["test_count"] < 20
        or tests.get("skipped_count") != 0
        or not isinstance(probe, dict)
        or probe.get("verdict") != "PASS"
        or probe.get("mismatch_count") != 0
        or probe.get("endpoint_failures") != 0
        or not isinstance(replay, dict)
        or replay.get("status") != "PASS"
        or replay.get("byte_deterministic") is not True
        or not isinstance(isolated, dict)
        or isolated.get("status") != "PASS"
        or isolated.get("rcdl003_runtime_importable") is not False
        or release.get("claim_boundary") != {
            "ace_level": "1_CANDIDATE",
            "promotion_authorized": False,
            "scientific_verdict": "LEARNED_PARITY",
            "same_builder": True,
            "independent_developer_or_lab": False,
            "neural_models_tested": False,
            "stochastic_llm_transport": "NOT_TESTED",
            "causal_equivalence": "NOT_ESTABLISHED",
        }
    ):
        raise EvidenceVerificationError("release sub-evidence did not pass")
    if (
        summary.get("schema") != "rcdl.learned-pressure-test-summary/0.4"
        or summary.get("scientific_verdict") != "LEARNED_PARITY"
        or summary.get("claim_effect") != RECEIPT_RESULT
        or summary.get("test_examples") != 1024
        or summary.get("rcdl_balanced_accuracy_ppm") != 1_000_000
        or summary.get("best_learned_balanced_accuracy_ppm") != 1_000_000
        or summary.get("promotion_authorized") is not False
    ):
        raise EvidenceVerificationError("pressure-test summary boundary failed")
    return tests, probe


def freeze_evidence(root: str | Path = EXPERIMENT_ROOT) -> dict[str, Any]:
    root_path = Path(root)
    evidence = root_path / "evidence"
    output = evidence / "pressure-test"
    manifest_path = output / "pressure-test-manifest.json"
    projection_path = output / "contract-projection.json"
    release_path = evidence / "release-check.json"
    for path in (manifest_path, projection_path, output / "predictions.jsonl", output / "summary.json", release_path):
        if not path.is_file():
            raise EvidenceVerificationError(f"missing required evidence: {path}")
    manifest = verify_manifest(manifest_path)
    projection = verify_projection(projection_path)
    binding = verify_frozen_bindings()
    release, summary = _release_and_summary(root_path)
    tests, probe = _validate_release(release, summary)
    if summary["manifest_digest"] != manifest.digest or summary["projection_digest"] != projection.digest:
        raise EvidenceVerificationError("pressure-test evidence binding failed")
    body = {
        "claim": RECEIPT_CLAIM,
        "result": RECEIPT_RESULT,
        "ace": {
            "experiment": "relational-contract-discovery-004",
            "level": "1_CANDIDATE",
            "promotion_authorized": False,
        },
        "source_tree_digest": source_tree_digest(root_path),
        "evidence": {
            "manifest_sha256": manifest.digest,
            "projection_sha256": projection.digest,
            "prediction_sha256": summary["prediction_digest"],
            "release_check_sha256": _sha256(release_path),
            "corpus_payload_sha256": binding.corpus_payload_sha256,
            "engine_aggregate_sha256": binding.engine_aggregate_sha256,
            "unit_tests": tests["test_count"],
            "randomized_comparisons": probe["comparisons"],
            "randomized_mismatches": probe["mismatch_count"],
            "test_examples": summary["test_examples"],
            "rcdl_balanced_accuracy_ppm": summary["rcdl_balanced_accuracy_ppm"],
            "best_learned_balanced_accuracy_ppm": summary["best_learned_balanced_accuracy_ppm"],
            "best_learned_model": summary["best_learned_model"],
        },
        "boundary": {
            "same_builder": True,
            "development_split_observed_and_excluded": True,
            "independent_developer_or_lab": False,
            "neural_models": "NOT_TESTED",
            "stochastic_llm_transport": "NOT_TESTED",
            "causal_equivalence": "NOT_ESTABLISHED",
            "policy_authority": "NONE",
        },
        "next_use": {
            "receipt_gate": "EVIDENCE_ATTACHMENT_ONLY",
            "claim_graph": "PREDICTIVE_SUPERIORITY_REJECTED_IN_BOUNDED_TOURNAMENT",
        },
    }
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "body": body,
        "body_digest": canonical_digest(body),
    }
    receipt_path = evidence / "experiment-receipt.json"
    receipt_digest = _write_bound_json(receipt, receipt_path)
    index_path = evidence / "evidence-index.json"
    index_sidecar = index_path.with_suffix(index_path.suffix + ".sha256")
    files = []
    for path in sorted(evidence.rglob("*")):
        if not path.is_file() or path in {index_path, index_sidecar}:
            continue
        files.append(
            {
                "path": path.relative_to(evidence).as_posix(),
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    index = {
        "schema": EVIDENCE_SCHEMA,
        "experiment": "relational-contract-discovery-004",
        "files": files,
    }
    index_digest = _write_bound_json(index, index_path)
    return {
        "frozen": True,
        "file_count": len(files),
        "receipt_digest": receipt_digest,
        "index_digest": index_digest,
    }


def verify_evidence(root: str | Path = EXPERIMENT_ROOT) -> dict[str, Any]:
    root_path = Path(root)
    evidence = root_path / "evidence"
    index_path = evidence / "evidence-index.json"
    receipt_path = evidence / "experiment-receipt.json"
    index, index_digest = _verify_bound_json(index_path)
    receipt, receipt_digest = _verify_bound_json(receipt_path)
    if (
        set(index) != {"schema", "experiment", "files"}
        or index.get("schema") != EVIDENCE_SCHEMA
        or index.get("experiment") != "relational-contract-discovery-004"
        or not isinstance(index.get("files"), list)
        or set(receipt) != {"schema", "body", "body_digest"}
        or receipt.get("schema") != RECEIPT_SCHEMA
    ):
        raise EvidenceVerificationError("unsupported frozen evidence schema")
    body = receipt["body"]
    if (
        not isinstance(body, dict)
        or body.get("claim") != RECEIPT_CLAIM
        or body.get("result") != RECEIPT_RESULT
        or canonical_digest(body) != receipt["body_digest"]
        or body.get("source_tree_digest") != source_tree_digest(root_path)
    ):
        raise EvidenceVerificationError("experiment receipt body mismatch")
    expected: dict[str, dict[str, Any]] = {}
    for item in index["files"]:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "size_bytes"}:
            raise EvidenceVerificationError("evidence index record is invalid")
        relative = item["path"]
        if not isinstance(relative, str) or not relative or relative.startswith("/") or ".." in Path(relative).parts or relative in expected:
            raise EvidenceVerificationError("evidence index path is invalid")
        expected[relative] = item
    actual = {
        path.relative_to(evidence).as_posix(): path
        for path in evidence.rglob("*")
        if path.is_file() and path not in {index_path, index_path.with_suffix(index_path.suffix + ".sha256")}
    }
    if set(actual) != set(expected):
        raise EvidenceVerificationError("frozen evidence closure mismatch")
    for relative, path in actual.items():
        item = expected[relative]
        if _sha256(path) != item["sha256"] or path.stat().st_size != item["size_bytes"]:
            raise EvidenceVerificationError(f"frozen evidence mismatch: {relative}")
    manifest = verify_manifest(evidence / "pressure-test" / "pressure-test-manifest.json")
    projection = verify_projection(evidence / "pressure-test" / "contract-projection.json")
    release, summary = _release_and_summary(root_path)
    tests, probe = _validate_release(release, summary)
    binding = verify_frozen_bindings()
    expected_evidence = {
        "manifest_sha256": manifest.digest,
        "projection_sha256": projection.digest,
        "prediction_sha256": summary["prediction_digest"],
        "release_check_sha256": _sha256(evidence / "release-check.json"),
        "corpus_payload_sha256": binding.corpus_payload_sha256,
        "engine_aggregate_sha256": binding.engine_aggregate_sha256,
        "unit_tests": tests["test_count"],
        "randomized_comparisons": probe["comparisons"],
        "randomized_mismatches": probe["mismatch_count"],
        "test_examples": summary["test_examples"],
        "rcdl_balanced_accuracy_ppm": summary["rcdl_balanced_accuracy_ppm"],
        "best_learned_balanced_accuracy_ppm": summary["best_learned_balanced_accuracy_ppm"],
        "best_learned_model": summary["best_learned_model"],
    }
    if body.get("evidence") != expected_evidence:
        raise EvidenceVerificationError("experiment receipt evidence binding mismatch")
    if body.get("boundary") != {
        "same_builder": True,
        "development_split_observed_and_excluded": True,
        "independent_developer_or_lab": False,
        "neural_models": "NOT_TESTED",
        "stochastic_llm_transport": "NOT_TESTED",
        "causal_equivalence": "NOT_ESTABLISHED",
        "policy_authority": "NONE",
    }:
        raise EvidenceVerificationError("experiment receipt boundary expanded")
    return {
        "verified": True,
        "file_count": len(expected),
        "receipt_digest": receipt_digest,
        "index_digest": index_digest,
        "scientific_verdict": manifest.scientific_verdict,
        "promotion_authorized": False,
    }

