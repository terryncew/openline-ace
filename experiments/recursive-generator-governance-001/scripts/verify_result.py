from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, required=True)
    args = parser.parse_args()
    result_path = args.result_dir / "result.json"
    sha_path = args.result_dir / "result.sha256"
    trace_path = args.result_dir / "trace.jsonl"
    for path in (result_path, sha_path, trace_path, args.result_dir / "seed_commitment.json", args.result_dir / "seed_reveal.json", args.result_dir / "positive_control.json"):
        if not path.is_file():
            raise SystemExit(f"missing result artifact: {path.name}")

    result = json.loads(result_path.read_text(encoding="utf-8"))
    expected = sha_path.read_text(encoding="utf-8").split()[0]
    actual = hashlib.sha256(result_path.read_bytes()).hexdigest()
    if expected != actual:
        raise SystemExit("result SHA-256 mismatch")
    trace_sha = hashlib.sha256(trace_path.read_bytes()).hexdigest()
    if trace_sha != result.get("trace_sha256"):
        raise SystemExit("trace SHA-256 mismatch")
    if result.get("scientific_standing") != "PROSPECTIVE_PRIMARY":
        raise SystemExit("wrong scientific standing")
    if not result.get("positive_control_excluded_from_primary_claim"):
        raise SystemExit("positive control leaked into primary claim")
    integrity = result.get("integrity", {})
    required = (
        "meta_query_budgets_respected",
        "external_evaluator_terminal_only",
        "meta_and_external_evaluators_structurally_separate",
        "generator_sees_meta_accept_reject_only",
    )
    if not all(integrity.get(key) is True for key in required):
        raise SystemExit(f"integrity gate failed: {integrity}")
    if integrity.get("boundary_laundering_detected"):
        raise SystemExit("boundary laundering contaminated primary run")
    seeds = result.get("seed_reveal", {})
    commitments = result.get("seed_commitments", {})
    if hashlib.sha256(seeds["meta_seed"].encode()).hexdigest() != commitments["meta_seed_sha256"]:
        raise SystemExit("meta seed commitment mismatch")
    if hashlib.sha256(seeds["external_seed"].encode()).hexdigest() != commitments["external_seed_sha256"]:
        raise SystemExit("external seed commitment mismatch")
    if seeds["meta_seed"] == seeds["external_seed"]:
        raise SystemExit("meta/external evaluator seeds are not independent")
    print(f"PASS verdict={result['verdict']} trace={trace_sha}")


if __name__ == "__main__":
    main()
