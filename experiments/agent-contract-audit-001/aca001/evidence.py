from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .canonical import file_digest, write_json
from .conformance import run_conformance
from .manifests import reduce_supported


EVIDENCE_FILES = (
    "observational-traces.jsonl",
    "conformance-results.jsonl",
    "contract-grades.json",
    "contract-manifests.json",
    "conformance-manifest.json",
    "verified-handoff-projection.json",
    "experiment-receipt.json",
)


def build_evidence(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    result = run_conformance()

    observational_path = output / "observational-traces.jsonl"
    observational_path.write_text(
        "".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            for row in result["observational_rows"]
        ),
        encoding="utf-8",
    )

    rows_path = output / "conformance-results.jsonl"
    rows_path.write_text(
        "".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            for row in result["rows"]
        ),
        encoding="utf-8",
    )

    grades_path = output / "contract-grades.json"
    write_json(grades_path, result["audit"])

    manifests = reduce_supported(result["candidates"], result["audit"]["grades"])
    manifests_path = output / "contract-manifests.json"
    write_json(manifests_path, manifests)

    manifest = {
        "experiment": "OpenLine Agent Contract Audit 001",
        "authority": "NONE",
        "verdict": result["verdict"],
        "scientific_standing": result["scientific_standing"],
        "blind_external_lane": result["blind_external_lane"],
        "pairs_per_candidate": result["pairs_per_candidate"],
        "policy": result["audit"]["policy"],
        "expected_standings": result["expected_standings"],
        "observed_standings": result["observed_standings"],
        "observational_summary": result["observational_summary"],
        "observational_sha256": file_digest(observational_path),
        "results_sha256": file_digest(rows_path),
        "grades_sha256": file_digest(grades_path),
        "contract_manifests_sha256": file_digest(manifests_path),
        "supported_manifest_count": len(manifests),
        "claim_boundary": (
            "This proves only conformance mechanics on a seeded stochastic fixture. "
            "It does not establish that the microscope separates real LLM-agent "
            "dependencies from rituals."
        ),
    }
    manifest_path = output / "conformance-manifest.json"
    write_json(manifest_path, manifest)

    projection = {
        "claim": (
            "The A-001 mechanism can separate two observationally indistinguishable "
            "fixture dependencies by causal intervention: retain the planted "
            "load-bearing relation, reject the planted ritual, abstain on a "
            "sham-sensitive confound, and ignore a wrapper-manufactured rule."
        ),
        "claim_effect": "MECHANICS_CONFORMANCE_ONLY",
        "external_agent_claim": "UNDECIDABLE_UNRUN",
        "manifest_sha256": file_digest(manifest_path),
        "contract_manifests_sha256": file_digest(manifests_path),
        "policy_authority": "NONE",
        "verdict": result["verdict"],
    }
    projection_path = output / "verified-handoff-projection.json"
    write_json(projection_path, projection)

    receipt = {
        "receipt_type": "openline.ace.experiment-receipt.v1",
        "experiment": "agent-contract-audit-001",
        "authority": "NONE",
        "status": "COMMIT",
        "scientific_standing": result["scientific_standing"],
        "observational_sha256": file_digest(observational_path),
        "results_sha256": file_digest(rows_path),
        "grades_sha256": file_digest(grades_path),
        "contract_manifests_sha256": file_digest(manifests_path),
        "manifest_sha256": file_digest(manifest_path),
        "projection_sha256": file_digest(projection_path),
        "blind_external_lane": "UNRUN",
    }
    receipt_path = output / "experiment-receipt.json"
    write_json(receipt_path, receipt)

    index = {
        name: {
            "sha256": file_digest(output / name),
            "size": (output / name).stat().st_size,
        }
        for name in EVIDENCE_FILES
    }
    write_json(output / "evidence-index.json", index)
    return result


def verify_evidence(output: Path) -> dict[str, Any]:
    index = json.loads((output / "evidence-index.json").read_text(encoding="utf-8"))
    if set(index) != set(EVIDENCE_FILES):
        raise RuntimeError("evidence index is not closed")
    for name, metadata in index.items():
        path = output / name
        if not path.exists():
            raise RuntimeError(f"missing evidence file: {name}")
        if path.stat().st_size != metadata["size"]:
            raise RuntimeError(f"size mismatch: {name}")
        if file_digest(path) != metadata["sha256"]:
            raise RuntimeError(f"digest mismatch: {name}")

    manifest = json.loads((output / "conformance-manifest.json").read_text(encoding="utf-8"))
    for field, name in (
        ("observational_sha256", "observational-traces.jsonl"),
        ("results_sha256", "conformance-results.jsonl"),
        ("grades_sha256", "contract-grades.json"),
        ("contract_manifests_sha256", "contract-manifests.json"),
    ):
        if manifest[field] != file_digest(output / name):
            raise RuntimeError(f"manifest does not bind {name}")

    if (
        manifest["observational_summary"]["validated_artifact_binding_prevalence_among_success"]
        != 1.0
        or manifest["observational_summary"]["format_scratchpad_prevalence_among_success"]
        != 1.0
    ):
        raise RuntimeError("observational pair is not equally correlated")

    manifests = json.loads((output / "contract-manifests.json").read_text(encoding="utf-8"))
    if len(manifests) != 1:
        raise RuntimeError("unexpected supported manifest count")
    if manifests[0]["policy_authority"] != "NONE" or manifests[0]["compiler_eligible"] is not False:
        raise RuntimeError("contract manifest authority boundary changed")

    projection = json.loads((output / "verified-handoff-projection.json").read_text(encoding="utf-8"))
    if projection["manifest_sha256"] != file_digest(output / "conformance-manifest.json"):
        raise RuntimeError("projection does not bind manifest")
    receipt = json.loads((output / "experiment-receipt.json").read_text(encoding="utf-8"))
    if receipt["projection_sha256"] != file_digest(output / "verified-handoff-projection.json"):
        raise RuntimeError("receipt does not bind projection")
    if receipt["status"] != "COMMIT" or receipt["authority"] != "NONE":
        raise RuntimeError("receipt boundary changed")
    return {
        "status": "VERIFIED",
        "verdict": manifest["verdict"],
        "scientific_standing": manifest["scientific_standing"],
    }
