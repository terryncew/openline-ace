"""Small canonical JSON and digest helpers used by RCDL-006."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def load_json_bytes(payload: bytes) -> Any:
    return json.loads(payload.decode("utf-8"))


def load_json(path: str | Path) -> Any:
    return load_json_bytes(Path(path).read_bytes())


def write_canonical(path: str | Path, value: Any) -> str:
    destination = Path(path)
    payload = canonical_json(value) + b"\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()

