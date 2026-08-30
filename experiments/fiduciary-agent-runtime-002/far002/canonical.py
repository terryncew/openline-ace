from __future__ import annotations
import hashlib, hmac, json
from dataclasses import asdict, is_dataclass


def _obj(x):
    if is_dataclass(x):
        return asdict(x)
    return x


def canonical_bytes(x) -> bytes:
    return (json.dumps(_obj(x), sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def sha256(x) -> str:
    if isinstance(x, bytes):
        b = x
    elif isinstance(x, str):
        b = x.encode()
    else:
        b = canonical_bytes(x)
    return hashlib.sha256(b).hexdigest()


def sign(secret: str, payload: dict) -> str:
    return hmac.new(secret.encode(), canonical_bytes(payload), hashlib.sha256).hexdigest()


def verify(secret: str, payload: dict, signature: str) -> bool:
    return hmac.compare_digest(sign(secret, payload), signature)
