"""Freeze and verify the experiment's bounded evidence package."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .canonical import canonical_digest, canonical_json, load_json_bytes
from .manifest import verify_manifest
from .projection import verify_projection
from .reference import verify_reference

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_SCHEMA = "openline.ace.evidence-index/0.1"
RECEIPT_SCHEMA = "openline.ace.experiment-receipt/0.1"


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
    entries = []
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


def freeze_evidence(root: str | Path = EXPERIMENT_ROOT) -> dict[str, Any]:
    root_path = Path(root)
    evidence = root_path / "evidence"
    calibration = evidence / "calibration"
    manifest_path = calibration / "contract-manifest.json"
    projection_path = calibration / "contract-projection.json"
    release_path = evidence / "release-check.json"
    summary_path = calibration / "summary.json"
    for required in (manifest_path, projection_path, release_path, summary_path):
        if not required.is_file():
            raise EvidenceVerificationError(f"missing required evidence: {required}")
    manifest = verify_manifest(manifest_path)
    projection = verify_projection(projection_path)
    projection_document = load_json_bytes(projection_path.read_bytes())
    reference = verify_reference(root_path / "references" / "official_raft_reference.json")
    release = load_json_bytes(release_path.read_bytes())
    summary = load_json_bytes(summary_path.read_bytes())
    if not isinstance(release, dict) or release.get("verdict") != "PASS":
        raise EvidenceVerificationError("release check did not pass")
    if not isinstance(summary, dict) or summary.get("verdict") != "CALIBRATION_PASS":
        raise EvidenceVerificationError("calibration summary did not pass")
    projection_source = (
        projection_document.get("source") if isinstance(projection_document, dict) else None
    )
    if (
        not isinstance(projection_source, dict)
        or projection_source.get("manifest_sha256") != manifest.digest
    ):
        raise EvidenceVerificationError("projection is not bound to the calibration manifest")
    if (
        summary.get("manifest_digest") != manifest.digest
        or summary.get("projection_digest") != projection.digest
    ):
        raise EvidenceVerificationError("calibration summary digest binding failed")
    release_unit_tests = release.get("unit_tests")
    release_probe = release.get("randomized_probe")
    if not isinstance(release_unit_tests, dict) or not isinstance(release_probe, dict):
        raise EvidenceVerificationError("release check evidence has an invalid shape")
    if (
        release_unit_tests.get("status") != "PASS"
        or release_probe.get("verdict") != "PASS"
        or release_probe.get("mismatch_count") != 0
    ):
        raise EvidenceVerificationError("release check sub-evidence did not pass")

    body = {
        "claim": "The bounded RCDL Raft micro-harness completed its declared local calibration.",
        "result": "SUPPORT_LOCAL_CALIBRATION_ONLY",
        "ace": {
            "experiment": "relational-contract-discovery-001",
            "level": "1_CANDIDATE",
            "promotion_authorized": False,
        },
        "source_tree_digest": source_tree_digest(root_path),
        "evidence": {
            "manifest_sha256": manifest.digest,
            "projection_sha256": projection.digest,
            "release_check_sha256": _sha256(release_path),
            "official_raft_sha256": reference.content_sha256,
            "unit_tests": release_unit_tests.get("test_count"),
            "randomized_comparisons": release_probe.get("comparisons"),
            "randomized_mismatches": release_probe.get("mismatch_count"),
            "trials_per_arm": summary["trials_per_arm"],
            "supported_clause_count": summary["supported_clause_count"],
            "spurious_control_rejected_count": summary[
                "spurious_control_rejected_count"
            ],
        },
        "boundary": {
            "tlc_execution": "NOT_RUN",
            "refinement_mapping": "NOT_MACHINE_CHECKED",
            "cross_implementation": "NOT_TESTED",
            "learned_agent_transport": "NOT_TESTED",
        },
        "next_use": {
            "receipt_gate": "EVIDENCE_ATTACHMENT_ONLY",
            "claim_graph": "LOCAL_CALIBRATION_STANDING",
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
        "experiment": "relational-contract-discovery-001",
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
    if index.get("schema") != EVIDENCE_SCHEMA or receipt.get("schema") != RECEIPT_SCHEMA:
        raise EvidenceVerificationError("unsupported frozen evidence schema")
    body = receipt.get("body")
    if not isinstance(body, dict) or canonical_digest(body) != receipt.get("body_digest"):
        raise EvidenceVerificationError("experiment receipt body mismatch")
    if body.get("source_tree_digest") != source_tree_digest(root_path):
        raise EvidenceVerificationError("source tree changed after evidence freeze")
    expected = {item["path"]: item for item in index.get("files", [])}
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
    release_path = evidence / "release-check.json"
    summary_path = evidence / "calibration" / "summary.json"
    manifest = verify_manifest(manifest_path)
    projection = verify_projection(projection_path)
    reference = verify_reference(root_path / "references" / "official_raft_reference.json")
    projection_document = load_json_bytes(projection_path.read_bytes())
    release = load_json_bytes(release_path.read_bytes())
    summary = load_json_bytes(summary_path.read_bytes())
    if not isinstance(projection_document, dict) or not isinstance(release, dict):
        raise EvidenceVerificationError("frozen evidence document has an invalid shape")
    if not isinstance(summary, dict):
        raise EvidenceVerificationError("calibration summary has an invalid shape")
    projection_source = projection_document.get("source")
    if not isinstance(projection_source, dict) or projection_source.get(
        "manifest_sha256"
    ) != manifest.digest:
        raise EvidenceVerificationError("projection manifest binding mismatch")
    if (
        summary.get("verdict") != "CALIBRATION_PASS"
        or summary.get("manifest_digest") != manifest.digest
        or summary.get("projection_digest") != projection.digest
    ):
        raise EvidenceVerificationError("calibration summary binding mismatch")
    if release.get("verdict") != "PASS":
        raise EvidenceVerificationError("frozen release check did not pass")
    release_unit_tests = release.get("unit_tests")
    release_probe = release.get("randomized_probe")
    if not isinstance(release_unit_tests, dict) or not isinstance(release_probe, dict):
        raise EvidenceVerificationError("frozen release check has an invalid shape")
    if (
        release_unit_tests.get("status") != "PASS"
        or release_probe.get("verdict") != "PASS"
        or release_probe.get("mismatch_count") != 0
    ):
        raise EvidenceVerificationError("frozen release check sub-evidence did not pass")
    expected_receipt_evidence = {
        "manifest_sha256": manifest.digest,
        "projection_sha256": projection.digest,
        "release_check_sha256": _sha256(release_path),
        "official_raft_sha256": reference.content_sha256,
        "unit_tests": release_unit_tests.get("test_count"),
        "randomized_comparisons": release_probe.get("comparisons"),
        "randomized_mismatches": release_probe.get("mismatch_count"),
        "trials_per_arm": summary.get("trials_per_arm"),
        "supported_clause_count": summary.get("supported_clause_count"),
        "spurious_control_rejected_count": summary.get(
            "spurious_control_rejected_count"
        ),
    }
    if body.get("evidence") != expected_receipt_evidence:
        raise EvidenceVerificationError("experiment receipt evidence binding mismatch")
    if body.get("ace") != {
        "experiment": "relational-contract-discovery-001",
        "level": "1_CANDIDATE",
        "promotion_authorized": False,
    }:
        raise EvidenceVerificationError("experiment receipt ACE boundary mismatch")
    if body.get("boundary") != {
        "tlc_execution": "NOT_RUN",
        "refinement_mapping": "NOT_MACHINE_CHECKED",
        "cross_implementation": "NOT_TESTED",
        "learned_agent_transport": "NOT_TESTED",
    }:
        raise EvidenceVerificationError("experiment receipt claim boundary mismatch")
    if body.get("next_use") != {
        "receipt_gate": "EVIDENCE_ATTACHMENT_ONLY",
        "claim_graph": "LOCAL_CALIBRATION_STANDING",
    }:
        raise EvidenceVerificationError("experiment receipt next-use boundary mismatch")
    return {
        "verified": True,
        "file_count": len(expected),
        "receipt_digest": receipt_digest,
        "index_digest": index_digest,
        "promotion_authorized": False,
    }
