from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from .core import audit_rows, dataset_sha256, load_policy
from .fixtures import SCHEMA, canonical_rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _snapshot_sha256(integration_hash: str, wrapper_hash: str) -> str:
    payload = json.dumps(
        {
            "integration_state_sha256": integration_hash,
            "wrapper_state_sha256": wrapper_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256_text(payload)


def unitree_risk_bucket(context: dict) -> str:
    force = float(context["push_force_newtons"])
    torque = abs(float(context["push_pitch_torque_nm"]))
    return f"force:{force:g}|abs_pitch_torque:{torque:g}"


def _verify_source_files(stage_a_dir: Path, manifest: dict) -> None:
    pins = {
        "intervention_sufficiency_input.csv": manifest["dataset_sha256"],
        "context_receipts.json": manifest["context_receipts_sha256"],
        "intervention_sufficiency_manifest.json": manifest[
            "stage_a_manifest_sha256"
        ],
    }
    for filename, expected in pins.items():
        path = stage_a_dir / filename
        if not path.is_file():
            raise ValueError(f"missing pinned Stage A file: {filename}")
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(
                f"Stage A hash mismatch for {filename}: expected {expected} got {actual}"
            )


def build_unitree_rows(stage_a_dir: Path, source_manifest: dict) -> list[dict]:
    _verify_source_files(stage_a_dir, source_manifest)
    upstream_manifest = json.loads(
        (stage_a_dir / "intervention_sufficiency_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    if upstream_manifest.get("evidence_mode") != "deterministic_rollout":
        raise ValueError("Stage A evidence mode changed")
    if not upstream_manifest.get("matching_frozen_before_outcome_analysis"):
        raise ValueError("Stage A matching procedure was not frozen")
    if (
        upstream_manifest.get("dataset_receipt_sha256")
        != source_manifest["dataset_sha256"]
    ):
        raise ValueError("Stage A manifest does not bind the pinned dataset")

    context_list = json.loads(
        (stage_a_dir / "context_receipts.json").read_text(encoding="utf-8")
    )
    contexts = {str(item["context_id"]): item for item in context_list}
    if len(contexts) != int(source_manifest["expected_contexts"]):
        raise ValueError("unexpected Stage A context count")

    source_rows: list[dict] = []
    with (stage_a_dir / "intervention_sufficiency_input.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        source_rows = list(csv.DictReader(handle))
    if len(source_rows) != int(source_manifest["expected_cells"]):
        raise ValueError("unexpected Stage A transition-cell count")

    dataset_id = (
        f"unitree-g1-stage-a-run-{int(source_manifest['stage_a_run_id'])}"
    )
    rows: list[dict] = []
    for index, source in enumerate(source_rows):
        context_id = str(source["context_id"])
        if context_id not in contexts:
            raise ValueError(f"transition row {index}: missing context receipt")
        context = contexts[context_id]
        outcome = str(source["outcome_success"])
        if outcome not in {"0", "1"}:
            raise ValueError(f"transition row {index}: invalid deterministic outcome")
        integration_hash = str(context["integration_state_sha256"])
        wrapper_hash = str(context["wrapper_state_sha256"])
        row = {
            "schema": SCHEMA,
            "dataset_id": dataset_id,
            "evidence_mode": "deterministic_rollout",
            "context_id": context_id,
            "snapshot_sha256": _snapshot_sha256(
                integration_hash, wrapper_hash
            ),
            "apparent_risk_bucket": unitree_risk_bucket(context),
            "action_id": str(source["action_id"]),
            "lag_ms": int(float(source["lag"])),
            "replicate": 0,
            "trial_id": f"{dataset_id}:{source['trial_id']}",
            "outcome_success": outcome == "1",
            "target_sha256": _sha256_text(str(source["target_id"])),
            "constraint_set_sha256": _sha256_text(
                str(source["constraint_set_id"])
            ),
            "policy_authority": "NONE",
        }
        rows.append(row)
    return rows


def run_external(
    *,
    stage_a_dir: Path,
    output_dir: Path,
    source_manifest_path: Path | None = None,
    policy_path: Path | None = None,
) -> dict:
    root = Path(__file__).resolve().parents[1]
    source_manifest_path = source_manifest_path or root / "SOURCE_MANIFEST.json"
    policy_path = policy_path or root / "PREREGISTRATION.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    policy = load_policy(policy_path)
    rows = build_unitree_rows(stage_a_dir, source_manifest)
    report = audit_rows(rows, policy)

    output_dir.mkdir(parents=True, exist_ok=True)
    canonical_path = output_dir / "unitree_canonical_rows.jsonl"
    canonical_path.write_text(
        "".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            for row in canonical_rows(rows)
        ),
        encoding="utf-8",
    )
    canonical_hash = sha256_file(canonical_path)
    if canonical_hash != dataset_sha256(rows):
        raise RuntimeError("canonical row serialization hash disagreement")

    result = {
        **report,
        "schema": "openline.ace.intervention-sufficiency.external-result.v2",
        "stage": "UNITREE_STAGE_A_RETROSPECTIVE_REPLAY",
        "scientific_standing": source_manifest["scientific_standing"],
        "source": {
            "repository": source_manifest["source_repository"],
            "commit": source_manifest["source_commit"],
            "stage_a_run_id": source_manifest["stage_a_run_id"],
            "dataset_sha256": source_manifest["dataset_sha256"],
            "context_receipts_sha256": source_manifest[
                "context_receipts_sha256"
            ],
            "stage_a_manifest_sha256": source_manifest[
                "stage_a_manifest_sha256"
            ],
            "unitree_repository": source_manifest["unitree_repository"],
            "unitree_commit": source_manifest["unitree_commit"],
        },
        "canonical_rows_sha256": canonical_hash,
        "prior_stage_b_run_id": source_manifest["prior_stage_b_run_id"],
        "prior_stage_b_regraded": False,
        "retrospective_reason": (
            "The source data and prior Stage B result existed before the 002 "
            "risk projection and thresholds were frozen."
        ),
    }
    result_path = output_dir / "unitree_external_result.json"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "unitree_external_result.sha256").write_text(
        f"{sha256_file(result_path)}  {result_path.name}\n", encoding="utf-8"
    )
    (output_dir / "unitree_canonical_rows.sha256").write_text(
        f"{canonical_hash}  {canonical_path.name}\n", encoding="utf-8"
    )
    return result
