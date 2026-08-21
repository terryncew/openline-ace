from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from .model import validate_candidate


def load_candidates(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError("candidate file must be a JSON array")
    return [validate_candidate(item) for item in value]


def run_external_proposer(
    command: Sequence[str], packet: Mapping[str, Any], timeout: float = 120.0
) -> list[dict[str, Any]]:
    proc = subprocess.run(
        list(command),
        input=(json.dumps(packet, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"proposer failed rc={proc.returncode}: {proc.stderr.decode('utf-8', 'replace')[:500]}"
        )
    value = json.loads(proc.stdout.decode("utf-8"))
    if not isinstance(value, list):
        raise ValueError("proposer must return a JSON array")
    return [validate_candidate(item) for item in value]
