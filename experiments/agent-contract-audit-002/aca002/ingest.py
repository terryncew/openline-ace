from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

REQUIRED = {
    "protocol", "candidate_id", "surface_id", "pair_id", "task_id", "seed", "arm",
    "runner_status", "verifier", "trace_sha256", "final_output_sha256", "provider"
}


def validate_result(value: dict[str, Any]) -> dict[str, Any]:
    missing = REQUIRED - set(value)
    if missing:
        raise ValueError(f"missing result fields: {sorted(missing)}")
    if value["protocol"] != "openline.agent-contract-audit.runner-result.v2":
        raise ValueError("wrong runner result protocol")
    if value["arm"] not in {"baseline", "active", "sham", "restoration"}:
        raise ValueError("invalid arm")
    verifier = value["verifier"]
    if set(verifier) != {"id", "success"} or type(verifier["success"]) is not bool:
        raise ValueError("invalid verifier projection")
    provider = value["provider"]
    if not isinstance(provider, dict) or not provider.get("kind"):
        raise ValueError("missing provider provenance")
    for field in ("trace_sha256", "final_output_sha256"):
        token = str(value[field])
        if len(token) != 64 or any(ch not in "0123456789abcdef" for ch in token):
            raise ValueError(f"invalid {field}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(validate_result(json.loads(line)))
        except Exception as exc:
            raise ValueError(f"invalid result line {line_no}: {exc}") from exc
    return rows


def verify_against_schedule(results: Iterable[dict[str, Any]], schedule: Iterable[dict[str, Any]]) -> None:
    expected = {
        (r["candidate_id"], r["surface_id"], r["pair_id"], r["task_id"], int(r["seed"]), r["arm"])
        for r in schedule
    }
    observed = []
    for r in results:
        observed.append((r["candidate_id"], r["surface_id"], r["pair_id"], r["task_id"], int(r["seed"]), r["arm"]))
    if len(observed) != len(set(observed)):
        raise ValueError("duplicate scheduled result")
    if set(observed) != expected:
        missing = expected - set(observed)
        extra = set(observed) - expected
        raise ValueError(f"result schedule mismatch missing={len(missing)} extra={len(extra)}")
