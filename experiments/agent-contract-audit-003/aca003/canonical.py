from __future__ import annotations
import hashlib, json
from typing import Any

SAFE_MIN = -9007199254740991
SAFE_MAX = 9007199254740991
_ESC = {'"':'\\"','\\':'\\\\','\b':'\\b','\f':'\\f','\n':'\\n','\r':'\\r','\t':'\\t'}

def _string(value: str) -> str:
    pieces = []
    for c in value:
        if c in _ESC:
            pieces.append(_ESC[c])
        elif ord(c) < 0x20 or ord(c) > 0x7f:
            pieces.append(f"\\u{ord(c):04x}")
        else:
            pieces.append(c)
    return '"' + "".join(pieces) + '"'

def canonical(value: Any) -> bytes:
    def enc(v: Any) -> str:
        if v is None: return "null"
        if v is True: return "true"
        if v is False: return "false"
        if type(v) is int:
            if not SAFE_MIN <= v <= SAFE_MAX:
                raise ValueError("integer outside canonical safe range")
            return str(v)
        if type(v) is float:
            raise ValueError("floats forbidden")
        if isinstance(v, str):
            return _string(v)
        if isinstance(v, list):
            return "[" + ",".join(enc(x) for x in v) + "]"
        if isinstance(v, dict):
            for k in v:
                if not isinstance(k, str) or any(ord(c) > 127 for c in k):
                    raise ValueError("object keys must be ASCII strings")
            return "{" + ",".join(_string(k)+":"+enc(v[k]) for k in sorted(v)) + "}"
        raise TypeError(type(v).__name__)
    return enc(value).encode("ascii")

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def object_hash(value: Any) -> str:
    return sha256_hex(canonical(value))

def conventional_json_hash(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256_hex(data)
