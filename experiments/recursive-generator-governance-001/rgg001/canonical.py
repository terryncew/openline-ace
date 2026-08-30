from __future__ import annotations

import hashlib
import json
from pathlib import Path


def canonical_bytes(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def canonical_sha256(obj) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class ReceiptChain:
    def __init__(self):
        self.prev = "0" * 64
        self.rows: list[dict] = []

    def append(self, event: dict) -> dict:
        row = {**event, "prev_receipt_sha256": self.prev}
        receipt = canonical_sha256(row)
        sealed = {**row, "receipt_sha256": receipt}
        self.rows.append(sealed)
        self.prev = receipt
        return sealed

    def write_jsonl(self, path: Path) -> None:
        path.write_text("".join(canonical_bytes(r).decode("utf-8") for r in self.rows), encoding="utf-8")
