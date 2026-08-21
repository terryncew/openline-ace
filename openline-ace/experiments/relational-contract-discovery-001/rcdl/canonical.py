"""Canonical JSON for the deliberately restricted RCDL data model."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any


class CanonicalizationError(ValueError):
    """Raised when a value is outside the canonical RCDL JSON subset."""


def _validate(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if not (-(2**63) <= value < 2**63):
            raise CanonicalizationError(f"{path}: integer is outside signed 64-bit range")
        return
    if isinstance(value, float):
        raise CanonicalizationError(f"{path}: floating-point values are forbidden")
    if isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            raise CanonicalizationError(f"{path}: string must be NFC-normalized")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError(f"{path}: object keys must be strings")
            _validate(key, f"{path}.<key>")
            _validate(item, f"{path}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        for index, item in enumerate(value):
            _validate(item, f"{path}[{index}]")
        return
    raise CanonicalizationError(f"{path}: unsupported value type {type(value).__name__}")


def canonical_json(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON for the constrained RCDL value space."""

    _validate(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    """Return the lowercase SHA-256 digest of canonical JSON."""

    return hashlib.sha256(canonical_json(value)).hexdigest()


def load_json_bytes(payload: bytes) -> Any:
    """Parse JSON and reject duplicate object keys before canonical validation."""

    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise CanonicalizationError(f"duplicate object key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=no_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanonicalizationError(f"invalid UTF-8 JSON: {exc}") from exc
    _validate(value)
    return value

