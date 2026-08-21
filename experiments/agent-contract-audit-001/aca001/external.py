from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical import sha256_bytes
from .model import ArmResult, validate_candidate


REQUEST_PROTOCOL = "openline.agent-contract-audit.runner-request.v1"
RESULT_PROTOCOL = "openline.agent-contract-audit.runner-result.v1"


def build_request(
    candidate: Mapping[str, Any],
    *,
    arm: str,
    pair_id: str,
    task_id: str,
    seed: int,
) -> dict[str, Any]:
    candidate = validate_candidate(candidate)
    if arm not in {"baseline", "active", "sham", "restoration"}:
        raise ValueError("invalid arm")
    intervention = (
        {"op": "none", "target": "workflow", "parameters": {}}
        if arm == "baseline"
        else candidate["interventions"][arm]
    )
    return {
        "protocol": REQUEST_PROTOCOL,
        "candidate_id": candidate["candidate_id"],
        "candidate_text": candidate["text"],
        "scope": candidate["scope"],
        "arm": arm,
        "pair_id": pair_id,
        "task_id": task_id,
        "seed": seed,
        "intervention": intervention,
        "authority": "NONE",
    }


def parse_result(request: Mapping[str, Any], raw: bytes) -> ArmResult:
    value = json.loads(raw.decode("utf-8"))
    if value.get("protocol") != RESULT_PROTOCOL:
        raise ValueError("runner result protocol mismatch")
    for key in ("candidate_id", "pair_id", "task_id", "seed", "arm"):
        if value.get(key) != request.get(key):
            raise ValueError(f"runner result binding mismatch: {key}")
    verifier = value.get("verifier")
    if not isinstance(verifier, dict):
        raise ValueError("runner result missing verifier")
    # Wrapper status may be recorded but never substitutes for original verifier success.
    mapped = {
        "candidate_id": value["candidate_id"],
        "pair_id": value["pair_id"],
        "task_id": value["task_id"],
        "seed": value["seed"],
        "arm": value["arm"],
        "verifier_id": verifier.get("id"),
        "verifier_success": verifier.get("success"),
        "runner_status": value.get("runner_status", "ok"),
        "trace_sha256": value.get("trace_sha256"),
    }
    return ArmResult.from_mapping(mapped)


def run_external(command: Sequence[str], request: Mapping[str, Any], timeout: float) -> ArmResult:
    proc = subprocess.run(
        list(command),
        input=(json.dumps(request, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"runner failed rc={proc.returncode}: {proc.stderr.decode('utf-8', 'replace')[:500]}"
        )
    return parse_result(request, proc.stdout)


def command_from_string(command: str) -> list[str]:
    parsed = shlex.split(command)
    if not parsed:
        raise ValueError("empty runner command")
    return parsed
