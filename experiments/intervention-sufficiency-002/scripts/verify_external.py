from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--expected", type=Path)
    args = parser.parse_args()

    result_path = args.result_dir / "unitree_external_result.json"
    rows_path = args.result_dir / "unitree_canonical_rows.jsonl"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    allowed = {
        "SUFFICIENT_FOR_FRESH_TRANSITION_CONFIRMATION",
        "INSUFFICIENT_STATE_SPECIFIC_INTERVENTION_CONTRAST",
    }
    if result.get("verdict") not in allowed:
        errors.append("invalid_or_unknown_verdict")
    if result.get("scientific_standing") != "RETROSPECTIVE_DIAGNOSTIC_ONLY":
        errors.append("scientific_standing")
    if result.get("prior_stage_b_regraded") is not False:
        errors.append("prior_stage_b_regraded")
    if result.get("capacity_selector_training_authorized") is not False:
        errors.append("selector_authority")
    if result.get("execution_authority") != "NONE":
        errors.append("execution_authority")
    if sha256_file(rows_path) != result.get("canonical_rows_sha256"):
        errors.append("canonical_rows_sha256")

    result_digest_path = args.result_dir / "unitree_external_result.sha256"
    recorded_result_digest = result_digest_path.read_text().split()[0]
    if recorded_result_digest != sha256_file(result_path):
        errors.append("result_sha256")
    rows_digest_path = args.result_dir / "unitree_canonical_rows.sha256"
    recorded_rows_digest = rows_digest_path.read_text().split()[0]
    if recorded_rows_digest != sha256_file(rows_path):
        errors.append("rows_sha256")
    if args.expected:
        expected = json.loads(args.expected.read_text(encoding="utf-8"))
        if result != expected:
            errors.append("canonical_result_mismatch")

    print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
