from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def canonical_sha(obj: dict) -> str:
    payload = (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--result-dir", type=Path, required=True)
    args = ap.parse_args()
    d = args.result_dir
    required = [
        "result.json", "result.sha256", "sealed_trajectories.json",
        "trace.jsonl", "seed_reveal.json", "progress_calibration.json"
    ]
    missing = [name for name in required if not (d / name).is_file()]
    if missing:
        raise SystemExit(f"missing result files {missing}")

    result = json.loads((d / "result.json").read_text(encoding="utf-8"))
    expected_result_sha = (d / "result.sha256").read_text(encoding="utf-8").split()[0]
    if sha256_file(d / "result.json") != expected_result_sha:
        raise SystemExit("result sha256 mismatch")
    if sha256_file(d / "sealed_trajectories.json") != result["trajectory_sha256"]:
        raise SystemExit("trajectory seal mismatch")

    reveal = json.loads((d / "seed_reveal.json").read_text(encoding="utf-8"))
    derived = hashlib.sha256(
        f"RGG002|{result['trajectory_sha256']}|{reveal['progress_nonce']}".encode("utf-8")
    ).hexdigest()
    if derived != reveal["progress_seed"]:
        raise SystemExit("progress seed does not derive from trajectory seal + nonce")
    if hashlib.sha256(reveal["progress_seed"].encode()).hexdigest() != result["seed_commitments"]["progress_seed_sha256"]:
        raise SystemExit("progress seed commitment mismatch")

    prev = "0" * 64
    saw_seal = False
    saw_progress_seed = False
    for line in (d / "trace.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        receipt = row.pop("receipt_sha256")
        if row.get("prev_receipt_sha256") != prev:
            raise SystemExit("receipt chain prev mismatch")
        if canonical_sha(row) != receipt:
            raise SystemExit("receipt hash mismatch")
        event = row.get("event")
        if event == "TRAJECTORIES_SEALED":
            saw_seal = True
        if event == "PROGRESS_SEED_DERIVED_AFTER_SEAL":
            if not saw_seal:
                raise SystemExit("progress seed event precedes trajectory seal")
            saw_progress_seed = True
        if event == "TERMINAL_PROGRESS_SCORE" and not saw_progress_seed:
            raise SystemExit("terminal progress score precedes post-seal seed")
        prev = receipt
    if prev != result["receipt_chain_head"]:
        raise SystemExit("receipt chain head mismatch")

    integrity = result["integrity"]
    if integrity["rgg001_external_holdout_reused"]:
        raise SystemExit("RGG-001 external holdout was reused")
    if not integrity["progress_evaluator_terminal_only"] or integrity["progress_feedback_returned_to_search"]:
        raise SystemExit("progress evaluator standing violation")
    print(f"PASS verdict={result['verdict']} trajectory={result['trajectory_sha256']} trace={result['trace_sha256']}")


if __name__ == "__main__":
    main()
