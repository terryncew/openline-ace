"""Freeze and verify the bounded RCDL-002 evidence package."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from rcdl.canonical import canonical_digest, canonical_json, load_json_bytes

from .engine_reference import verify_engine_reference
from .manifest import verify_manifest
from .projection import verify_projection

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_SCHEMA = "openline.ace.evidence-index/0.1"
RECEIPT_SCHEMA = "openline.ace.experiment-receipt/0.1"
RECEIPT_CLAIM = (
    "The frozen RCDL 0.1 engine transported to a deterministic repair workflow "
    "and identified local bounded recovery."
)
RECEIPT_RESULT = "SUPPORT_LOCAL_DETERMINISTIC_TRANSPORT_ONLY"


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
        raise EvidenceVerificationError(f"non-canonical bound JSON: {path.name}")
    digest = hashlib.sha256(payload).hexdigest()
    sidecar = path.with_suffix(path.suffix + ".sha256")
    parts = sidecar.read_text(encoding="utf-8").strip().split() if sidecar.is_file() else []
    if len(parts) != 2 or parts[0] != digest or parts[1] != path.name:
        raise EvidenceVerificationError(f"sidecar mismatch: {path.name}")
    return document, digest


def _source_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if "evidence" in relative.parts or "__pycache__" in relative.parts:
            continue
        if path.suffix == ".pyc":
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


def _load_release_and_summary(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    release = load_json_bytes((root / "evidence" / "release-check.json").read_bytes())
    summary = load_json_bytes(
        (root / "evidence" / "calibration" / "summary.json").read_bytes()
    )
    if not isinstance(release, dict) or not isinstance(summary, dict):
        raise EvidenceVerificationError("release or summary evidence has an invalid shape")
    return release, summary


def _validate_release_and_summary(
    release: dict[str, Any], summary: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    tests = release.get("unit_tests")
    probe = release.get("randomized_probe")
    calibration = release.get("calibration")
    isolated = release.get("isolated_copy")
    boundary = release.get("claim_boundary")
    if (
        release.get("verdict") != "PASS"
        or release.get("compileall") != "PASS"
        or not isinstance(tests, dict)
        or tests.get("status") != "PASS"
        or isinstance(tests.get("test_count"), bool)
        or not isinstance(tests.get("test_count"), int)
        or tests["test_count"] < 1
        or tests.get("skipped_count") not in {0, 1}
        or not isinstance(probe, dict)
        or probe.get("verdict") != "PASS"
        or probe.get("mismatch_count") != 0
        or isinstance(probe.get("comparisons"), bool)
        or not isinstance(probe.get("comparisons"), int)
        or probe["comparisons"] < 1
        or not isinstance(calibration, dict)
        or calibration.get("status") != "PASS"
        or calibration.get("deterministic_replay") is not True
        or not isinstance(isolated, dict)
        or isolated.get("status") != "PASS"
        or isolated.get("outside_repository_context") is not True
        or boundary
        != {
            "ace_level": "1_CANDIDATE",
            "promotion_authorized": False,
            "independent_implementation": "NOT_TESTED",
            "stochastic_llm_transport": "NOT_TESTED",
        }
    ):
        raise EvidenceVerificationError("release sub-evidence did not pass")
    if (
        summary.get("schema") != "rcdl.calibration-summary/0.2"
        or summary.get("verdict") != "CALIBRATION_PASS"
        or summary.get("candidate_clause_count") != 5
        or summary.get("supported_clause_count") != 4
        or summary.get("rejected_clause_count") != 1
        or summary.get("spurious_control_rejected_count") != 1
        or summary.get("minimal_family_count") != 1
        or summary.get("bounded_recovery_supported_count") != 1
        or summary.get("engine_modified") is not False
        or isinstance(summary.get("trials_per_arm"), bool)
        or not isinstance(summary.get("trials_per_arm"), int)
        or not 2 <= summary["trials_per_arm"] <= 64
    ):
        raise EvidenceVerificationError("calibration summary boundary failed")
    return tests, probe


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def freeze_evidence(root: str | Path = EXPERIMENT_ROOT) -> dict[str, Any]:
    root_path = Path(root)
    evidence = root_path / "evidence"
    calibration = evidence / "calibration"
    manifest_path = calibration / "contract-manifest.json"
    projection_path = calibration / "contract-projection.json"
    summary_path = calibration / "summary.json"
    release_path = evidence / "release-check.json"
    for required in (manifest_path, projection_path, summary_path, release_path):
        if not required.is_file():
            raise EvidenceVerificationError(f"missing required evidence: {required}")
    manifest = verify_manifest(manifest_path)
    projection = verify_projection(projection_path)
    engine = verify_engine_reference(root_path / "references" / "rcdl_0_1_engine_reference.json")
    release, summary = _load_release_and_summary(root_path)
    projection_document = load_json_bytes(projection_path.read_bytes())
    tests, probe = _validate_release_and_summary(release, summary)
    if (
        not isinstance(projection_document, dict)
        or projection_document.get("source", {}).get("manifest_sha256") != manifest.digest
        or summary.get("manifest_digest") != manifest.digest
        or summary.get("projection_digest") != projection.digest
    ):
        raise EvidenceVerificationError("calibration evidence binding failed")
    body = {
        "claim": RECEIPT_CLAIM,
        "result": RECEIPT_RESULT,
        "ace": {
            "experiment": "relational-contract-discovery-002",
            "level": "1_CANDIDATE",
            "promotion_authorized": False,
        },
        "source_tree_digest": source_tree_digest(root_path),
        "evidence": {
            "manifest_sha256": manifest.digest,
            "projection_sha256": projection.digest,
            "release_check_sha256": _sha256(release_path),
            "engine_aggregate_sha256": engine.aggregate_sha256,
            "unit_tests": tests.get("test_count"),
            "randomized_comparisons": probe.get("comparisons"),
            "randomized_mismatches": probe.get("mismatch_count"),
            "trials_per_arm": summary.get("trials_per_arm"),
            "supported_clause_count": summary.get("supported_clause_count"),
            "spurious_control_rejected_count": summary.get(
                "spurious_control_rejected_count"
            ),
            "bounded_recovery_supported_count": summary.get(
                "bounded_recovery_supported_count"
            ),
        },
        "boundary": {
            "engine_modified": False,
            "independent_implementation": "NOT_TESTED",
            "stochastic_llm_transport": "NOT_TESTED",
            "token_timing_sham_matching": "NOT_TESTED",
            "open_ended_discovery": "NOT_TESTED",
        },
        "next_use": {
            "receipt_gate": "EVIDENCE_ATTACHMENT_ONLY",
            "claim_graph": "LOCAL_DETERMINISTIC_TRANSPORT_STANDING",
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
        "experiment": "relational-contract-discovery-002",
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
        or set(receipt) != {"schema", "body", "body_digest"}
        or not isinstance(index.get("files"), list)
        or index.get("schema") != EVIDENCE_SCHEMA
        or index.get("experiment") != "relational-contract-discovery-002"
        or receipt.get("schema") != RECEIPT_SCHEMA
    ):
        raise EvidenceVerificationError("unsupported frozen evidence schema")
    body = receipt.get("body")
    if (
        not isinstance(body, dict)
        or set(body)
        != {
            "claim",
            "result",
            "ace",
            "source_tree_digest",
            "evidence",
            "boundary",
            "next_use",
        }
        or body.get("claim") != RECEIPT_CLAIM
        or body.get("result") != RECEIPT_RESULT
        or canonical_digest(body) != receipt.get("body_digest")
    ):
        raise EvidenceVerificationError("experiment receipt body mismatch")
    if body.get("source_tree_digest") != source_tree_digest(root_path):
        raise EvidenceVerificationError("source tree changed after evidence freeze")
    expected: dict[str, dict[str, Any]] = {}
    for item in index["files"]:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "size_bytes"}:
            raise EvidenceVerificationError("frozen evidence index record is invalid")
        relative = item["path"]
        size = item["size_bytes"]
        if (
            not isinstance(relative, str)
            or not relative
            or relative.startswith("/")
            or ".." in Path(relative).parts
            or relative in expected
            or not _is_sha256(item["sha256"])
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
        ):
            raise EvidenceVerificationError("frozen evidence index values are invalid")
        expected[relative] = item
    actual_paths = {
        path.relative_to(evidence).as_posix(): path
        for path in evidence.rglob("*")
        if path.is_file()
        and path not in {index_path, index_path.with_suffix(index_path.suffix + ".sha256")}
    }
    if set(expected) != set(actual_paths):
        raise EvidenceVerificationError("frozen evidence closure mismatch")
    for relative, path in actual_paths.items():
        item = expected[relative]
        if item.get("sha256") != _sha256(path) or item.get("size_bytes") != path.stat().st_size:
            raise EvidenceVerificationError(f"frozen evidence mismatch: {relative}")

    manifest_path = evidence / "calibration" / "contract-manifest.json"
    projection_path = evidence / "calibration" / "contract-projection.json"
    summary_path = evidence / "calibration" / "summary.json"
    release_path = evidence / "release-check.json"
    manifest = verify_manifest(manifest_path)
    projection = verify_projection(projection_path)
    engine = verify_engine_reference(root_path / "references" / "rcdl_0_1_engine_reference.json")
    release, summary = _load_release_and_summary(root_path)
    projection_document = load_json_bytes(projection_path.read_bytes())
    if (
        not isinstance(projection_document, dict)
        or projection_document.get("source", {}).get("manifest_sha256") != manifest.digest
        or summary.get("verdict") != "CALIBRATION_PASS"
        or summary.get("manifest_digest") != manifest.digest
        or summary.get("projection_digest") != projection.digest
        or release.get("verdict") != "PASS"
    ):
        raise EvidenceVerificationError("frozen evidence binding failed")
    tests, probe = _validate_release_and_summary(release, summary)
    expected_receipt_evidence = {
        "manifest_sha256": manifest.digest,
        "projection_sha256": projection.digest,
        "release_check_sha256": _sha256(release_path),
        "engine_aggregate_sha256": engine.aggregate_sha256,
        "unit_tests": tests.get("test_count") if isinstance(tests, dict) else None,
        "randomized_comparisons": probe.get("comparisons") if isinstance(probe, dict) else None,
        "randomized_mismatches": probe.get("mismatch_count") if isinstance(probe, dict) else None,
        "trials_per_arm": summary.get("trials_per_arm"),
        "supported_clause_count": summary.get("supported_clause_count"),
        "spurious_control_rejected_count": summary.get("spurious_control_rejected_count"),
        "bounded_recovery_supported_count": summary.get("bounded_recovery_supported_count"),
    }
    if body.get("evidence") != expected_receipt_evidence:
        raise EvidenceVerificationError("experiment receipt evidence binding mismatch")
    if body.get("ace") != {
        "experiment": "relational-contract-discovery-002",
        "level": "1_CANDIDATE",
        "promotion_authorized": False,
    }:
        raise EvidenceVerificationError("experiment receipt ACE boundary mismatch")
    if body.get("boundary") != {
        "engine_modified": False,
        "independent_implementation": "NOT_TESTED",
        "stochastic_llm_transport": "NOT_TESTED",
        "token_timing_sham_matching": "NOT_TESTED",
        "open_ended_discovery": "NOT_TESTED",
    }:
        raise EvidenceVerificationError("experiment receipt claim boundary mismatch")
    if body.get("next_use") != {
        "receipt_gate": "EVIDENCE_ATTACHMENT_ONLY",
        "claim_graph": "LOCAL_DETERMINISTIC_TRANSPORT_STANDING",
    }:
        raise EvidenceVerificationError("experiment receipt next-use boundary mismatch")
    return {
        "verified": True,
        "file_count": len(expected),
        "receipt_digest": receipt_digest,
        "index_digest": index_digest,
        "promotion_authorized": False,
    }
