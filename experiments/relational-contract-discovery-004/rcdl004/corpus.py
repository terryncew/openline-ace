"""Load and fail-closed verify the frozen RCDL-004 learning corpus."""

from __future__ import annotations

import gzip
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rcdl.canonical import canonical_digest, canonical_json, load_json_bytes
from rcdl.trace import Trace

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = EXPERIMENT_ROOT / "references" / "frozen-learning-corpus.jsonl.gz"
MANIFEST_PATH = EXPERIMENT_ROOT / "references" / "frozen-learning-corpus-manifest.json"
EXPECTED_SPLITS = {"train": 640, "validation": 160, "test": 1024}
FORBIDDEN_TRACE_FIELDS = frozenset(
    {"arm", "failed", "hook", "intervention_arm", "oracle", "oracle_passed", "target"}
)


class CorpusVerificationError(ValueError):
    pass


@dataclass(frozen=True)
class LearningExample:
    example_id: str
    split: str
    trace: Trace
    failed: bool


@dataclass(frozen=True)
class FrozenCorpus:
    examples: tuple[LearningExample, ...]
    compressed_sha256: str
    payload_sha256: str

    def split(self, name: str) -> tuple[LearningExample, ...]:
        if name not in EXPECTED_SPLITS:
            raise ValueError(f"unknown corpus split: {name}")
        return tuple(row for row in self.examples if row.split == name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": True,
            "compressed_sha256": self.compressed_sha256,
            "payload_sha256": self.payload_sha256,
            "row_count": len(self.examples),
            "split_counts": {name: len(self.split(name)) for name in EXPECTED_SPLITS},
            "direct_labels_in_trace": False,
        }


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(key)
            keys.update(_walk_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_walk_keys(item))
    return keys


def _parse_payload(payload: bytes) -> tuple[LearningExample, ...]:
    rows: list[LearningExample] = []
    seen: set[str] = set()
    previous_order: tuple[int, str] | None = None
    order = {"train": 0, "validation": 1, "test": 2}
    for line_number, raw_line in enumerate(payload.splitlines(), 1):
        if not raw_line:
            raise CorpusVerificationError(f"blank corpus line: {line_number}")
        document = load_json_bytes(raw_line)
        if not isinstance(document, dict) or set(document) != {
            "schema", "example_id", "split", "failed", "trace"
        }:
            raise CorpusVerificationError(f"invalid corpus row: {line_number}")
        if document["schema"] != "rcdl.learning-example/0.1":
            raise CorpusVerificationError("unsupported learning-example schema")
        if raw_line != canonical_json(document):
            raise CorpusVerificationError(f"non-canonical corpus row: {line_number}")
        split = document["split"]
        failed = document["failed"]
        example_id = document["example_id"]
        if (
            split not in EXPECTED_SPLITS
            or not isinstance(failed, bool)
            or not isinstance(example_id, str)
            or len(example_id) != 64
            or any(character not in "0123456789abcdef" for character in example_id)
            or example_id in seen
        ):
            raise CorpusVerificationError(f"invalid corpus identity: {line_number}")
        trace_document = document["trace"]
        if not isinstance(trace_document, dict):
            raise CorpusVerificationError("trace document must be an object")
        forbidden = _walk_keys(trace_document) & FORBIDDEN_TRACE_FIELDS
        if forbidden:
            raise CorpusVerificationError(f"direct labels leaked into trace: {sorted(forbidden)}")
        expected_id = canonical_digest(
            {"split": split, "failed": failed, "trace": trace_document}
        )
        if example_id != expected_id:
            raise CorpusVerificationError(f"example identity mismatch: {line_number}")
        current_order = (order[split], example_id)
        if previous_order is not None and current_order <= previous_order:
            raise CorpusVerificationError("corpus rows are not strictly ordered")
        previous_order = current_order
        seen.add(example_id)
        rows.append(LearningExample(example_id, split, Trace.from_dict(trace_document), failed))
    return tuple(rows)


def load_frozen_corpus() -> FrozenCorpus:
    compressed = CORPUS_PATH.read_bytes()
    manifest_payload = MANIFEST_PATH.read_bytes()
    manifest = load_json_bytes(manifest_payload)
    if not isinstance(manifest, dict) or manifest_payload != canonical_json(manifest) + b"\n":
        raise CorpusVerificationError("corpus manifest is not canonical")
    expected_keys = {
        "schema", "generator", "compressed_sha256", "payload_sha256",
        "row_count", "splits", "label_boundary", "source_bindings"
    }
    if set(manifest) != expected_keys or manifest["schema"] != "rcdl.frozen-learning-corpus/0.1":
        raise CorpusVerificationError("corpus manifest closure failed")
    compressed_digest = _sha256(compressed)
    if compressed_digest != manifest["compressed_sha256"]:
        raise CorpusVerificationError("compressed corpus digest mismatch")
    try:
        payload = gzip.decompress(compressed)
    except (OSError, EOFError) as exc:
        raise CorpusVerificationError(f"corpus decompression failed: {exc}") from exc
    payload_digest = _sha256(payload)
    if payload_digest != manifest["payload_sha256"]:
        raise CorpusVerificationError("corpus payload digest mismatch")
    rows = _parse_payload(payload)
    split_counts = {name: sum(row.split == name for row in rows) for name in EXPECTED_SPLITS}
    if (
        manifest["row_count"] != len(rows)
        or manifest["splits"] != split_counts
        or split_counts != EXPECTED_SPLITS
        or manifest["label_boundary"]
        != {
            "labels_available_during_training": True,
            "labels_unavailable_at_prediction": True,
            "intervention_labels_in_trace": False,
            "oracle_values_in_trace": False,
            "raw_identity_values_allowed_as_features": False,
        }
    ):
        raise CorpusVerificationError("corpus split or label boundary mismatch")
    for name in EXPECTED_SPLITS:
        if {row.failed for row in rows if row.split == name} != {False, True}:
            raise CorpusVerificationError(f"corpus split lost an outcome class: {name}")
    return FrozenCorpus(rows, compressed_digest, payload_digest)

