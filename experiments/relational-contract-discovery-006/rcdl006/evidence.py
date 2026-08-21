"""Freeze and verify the bounded RCDL-006 evidence package."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .canonical import canonical_digest, canonical_json, load_json_bytes
from .tournament import CLAIM_EFFECT, SCIENTIFIC_VERDICT
from .verification import verify_manifest, verify_projection


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_SCHEMA = "openline.ace.evidence-index/0.1"
RECEIPT_SCHEMA = "openline.ace.experiment-receipt/0.1"
RECEIPT_RESULT = "HELD_OUT_MECHANISM_CAUSAL_PARITY"
RECEIPT_CLAIM = (
    "Using pinned EnvHarness core only as a non-authoritative intervention substrate, "
    "symbolic RCDL and a learned signature baseline both distinguished native verifier-"
    "relevant failures from wrapper-imposed and nuisance mechanisms across held-out "
    "compositions and agent implementations; neither showed unique advantage."
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_bound(document: dict[str, Any], path: Path) -> str:
    payload = canonical_json(document) + b"\n"
    path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    path.with_suffix(path.suffix + ".sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def _verify_bound(path: Path) -> tuple[dict[str, Any], str]:
    payload = path.read_bytes()
    document = load_json_bytes(payload)
    if not isinstance(document, dict) or payload != canonical_json(document) + b"\n":
        raise ValueError(f"non-canonical evidence: {path.name}")
    digest = hashlib.sha256(payload).hexdigest()
    sidecar = path.with_suffix(path.suffix + ".sha256")
    parts = sidecar.read_text(encoding="utf-8").strip().split() if sidecar.is_file() else []
    if parts != [digest, path.name]:
        raise ValueError(f"evidence sidecar mismatch: {path.name}")
    return document, digest


def _source_entries(root: Path) -> list[dict[str, Any]]:
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if "evidence" in relative.parts or "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        entries.append({"path": relative.as_posix(), "sha256": _sha256(path), "size_bytes": path.stat().st_size})
    return entries


def source_tree_digest(root: str | Path = EXPERIMENT_ROOT) -> str:
    return canonical_digest(_source_entries(Path(root)))


def _load_release(root: Path) -> dict[str, Any]:
    document = load_json_bytes((root / "evidence" / "release-check.json").read_bytes())
    if not isinstance(document, dict):
        raise ValueError("release check is invalid")
    if (
        document.get("schema") != "rcdl.release-check/0.6"
        or document.get("verdict") != "PASS"
        or document.get("compileall") != "PASS"
        or document.get("deterministic_replay") != "PASS"
        or document.get("fixture_boundary") != "PASS"
        or document.get("isolated_copy") != "PASS"
        or document.get("manifest_projection") != "PASS"
        or document.get("policy_boundary") != "PASS"
        or document.get("upstream_boundary") != "PASS"
        or document.get("unit_tests", {}).get("status") != "PASS"
        or document.get("unit_tests", {}).get("test_count", 0) < 35
        or document.get("randomized_probe", {}).get("status") != "PASS"
        or document.get("randomized_probe", {}).get("comparisons", 0) < 4096
        or document.get("randomized_probe", {}).get("mismatches") != 0
    ):
        raise ValueError("release check did not pass")
    return document


def freeze_evidence(root: str | Path = EXPERIMENT_ROOT) -> dict[str, Any]:
    root_path = Path(root)
    evidence = root_path / "evidence"
    output = evidence / "heldout-mechanism"
    manifest = verify_manifest(output / "heldout-mechanism-manifest.json")
    projection = verify_projection(output / "verified-handoff-projection.json")
    release = _load_release(root_path)
    summary = load_json_bytes((output / "summary.json").read_bytes())
    if not isinstance(summary, dict) or summary.get("scientific_verdict") != SCIENTIFIC_VERDICT:
        raise ValueError("summary scientific boundary failed")
    if summary.get("manifest_digest") != manifest.digest or summary.get("projection_digest") != projection.digest:
        raise ValueError("summary evidence binding failed")
    body = {
        "ace": {"experiment": "relational-contract-discovery-006", "level": "1_CANDIDATE", "promotion_authorized": False},
        "boundary": {
            "actual_envharness_core": True,
            "external_preregistration": False,
            "independent_replication": False,
            "live_envrigger_generation": False,
            "original_verifier_only": True,
            "policy_authority": "NONE",
            "same_builder": True,
            "stochastic_llm_transport": "NOT_TESTED",
        },
        "claim": RECEIPT_CLAIM,
        "evidence": {
            "manifest_sha256": manifest.digest,
            "projection_sha256": projection.digest,
            "randomized_comparisons": release["randomized_probe"]["comparisons"],
            "randomized_mismatches": release["randomized_probe"]["mismatches"],
            "release_check_sha256": _sha256(evidence / "release-check.json"),
            "result_rows": summary["result_rows"],
            "results_sha256": summary["results_digest"],
            "unit_tests": release["unit_tests"]["test_count"],
            "upstream_commit": "fab7d57441f06b75c73a900e04561d4d7600f361",
        },
        "next_use": {
            "claim_graph": "NATIVE_VS_IMPOSED_DISTINCTION_SUPPORTED_UNIQUE_ADVANTAGE_NOT_FOUND",
            "receipt_gate": "EVIDENCE_ATTACHMENT_ONLY",
        },
        "result": RECEIPT_RESULT,
        "source_tree_digest": source_tree_digest(root_path),
    }
    receipt = {"body": body, "body_digest": canonical_digest(body), "schema": RECEIPT_SCHEMA}
    receipt_digest = _write_bound(receipt, evidence / "experiment-receipt.json")
    index_path = evidence / "evidence-index.json"
    index_sidecar = index_path.with_suffix(index_path.suffix + ".sha256")
    files = []
    for path in sorted(evidence.rglob("*")):
        if path.is_file() and path not in {index_path, index_sidecar}:
            files.append({"path": path.relative_to(evidence).as_posix(), "sha256": _sha256(path), "size_bytes": path.stat().st_size})
    index = {"experiment": "relational-contract-discovery-006", "files": files, "schema": EVIDENCE_SCHEMA}
    index_digest = _write_bound(index, index_path)
    return {"file_count": len(files), "frozen": True, "index_digest": index_digest, "receipt_digest": receipt_digest}


def verify_evidence(root: str | Path = EXPERIMENT_ROOT) -> dict[str, Any]:
    root_path = Path(root)
    evidence = root_path / "evidence"
    index_path = evidence / "evidence-index.json"
    index, index_digest = _verify_bound(index_path)
    receipt, receipt_digest = _verify_bound(evidence / "experiment-receipt.json")
    if set(index) != {"experiment", "files", "schema"} or index.get("schema") != EVIDENCE_SCHEMA or index.get("experiment") != "relational-contract-discovery-006":
        raise ValueError("evidence index schema failed")
    if set(receipt) != {"body", "body_digest", "schema"} or receipt.get("schema") != RECEIPT_SCHEMA:
        raise ValueError("receipt schema failed")
    body = receipt["body"]
    if (
        not isinstance(body, dict)
        or body.get("claim") != RECEIPT_CLAIM
        or body.get("result") != RECEIPT_RESULT
        or canonical_digest(body) != receipt["body_digest"]
        or body.get("source_tree_digest") != source_tree_digest(root_path)
        or body.get("boundary", {}).get("policy_authority") != "NONE"
        or body.get("boundary", {}).get("live_envrigger_generation") is not False
    ):
        raise ValueError("receipt body binding failed")
    expected: dict[str, dict[str, Any]] = {}
    for item in index["files"]:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "size_bytes"}:
            raise ValueError("evidence index record failed")
        relative = item["path"]
        if not isinstance(relative, str) or not relative or relative.startswith("/") or ".." in Path(relative).parts or relative in expected:
            raise ValueError("evidence index path failed")
        expected[relative] = item
    excluded = {index_path, index_path.with_suffix(index_path.suffix + ".sha256")}
    actual = {path.relative_to(evidence).as_posix(): path for path in evidence.rglob("*") if path.is_file() and path not in excluded}
    if set(actual) != set(expected):
        raise ValueError("frozen evidence closure mismatch")
    for relative, path in actual.items():
        item = expected[relative]
        if _sha256(path) != item["sha256"] or path.stat().st_size != item["size_bytes"]:
            raise ValueError(f"frozen evidence mismatch: {relative}")
    manifest = verify_manifest(evidence / "heldout-mechanism" / "heldout-mechanism-manifest.json")
    projection = verify_projection(evidence / "heldout-mechanism" / "verified-handoff-projection.json")
    release = _load_release(root_path)
    summary = load_json_bytes((evidence / "heldout-mechanism" / "summary.json").read_bytes())
    expected_pointers = {
        "manifest_sha256": manifest.digest,
        "projection_sha256": projection.digest,
        "randomized_comparisons": release["randomized_probe"]["comparisons"],
        "randomized_mismatches": release["randomized_probe"]["mismatches"],
        "release_check_sha256": _sha256(evidence / "release-check.json"),
        "result_rows": summary["result_rows"],
        "results_sha256": summary["results_digest"],
        "unit_tests": release["unit_tests"]["test_count"],
        "upstream_commit": "fab7d57441f06b75c73a900e04561d4d7600f361",
    }
    if body.get("evidence") != expected_pointers:
        raise ValueError("receipt evidence pointers changed")
    return {
        "file_count": len(expected),
        "index_digest": index_digest,
        "policy_authority": "NONE",
        "receipt_digest": receipt_digest,
        "scientific_verdict": SCIENTIFIC_VERDICT,
        "verified": True,
    }
