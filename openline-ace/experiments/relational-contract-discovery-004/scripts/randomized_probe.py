#!/usr/bin/env python3
"""Randomized nuisance and identity-erasure probe for RCDL-004."""

from __future__ import annotations

import argparse
import copy
import json
import random
from typing import Any

from rcdl.canonical import canonical_digest
from rcdl.evaluator import evaluate
from rcdl.nuisance import nuisance_variants
from rcdl.otel import trace_from_otlp, trace_to_otlp
from rcdl.trace import Trace

from rcdl004.corpus import load_frozen_corpus
from rcdl004.features import combined_features, graph_features, sequence_features
from rcdl004.tournament import _frozen_target_clauses


def _signature(trace: Trace) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    return sequence_features(trace), graph_features(trace), combined_features(trace)


def _evaluation_signature(trace: Trace) -> tuple[tuple[str, bool, int, int, int], ...]:
    return tuple(
        (
            clause.id,
            result.passed,
            result.trigger_count,
            result.support_count,
            result.violation_count,
        )
        for clause in _frozen_target_clauses()
        for result in (evaluate(clause, trace),)
    )


def _remap_identities(trace: Trace, salt: int) -> Trace:
    document = trace.to_dict()
    mappings: dict[tuple[str, str], str] = {}
    for event in document["events"]:
        for key in ("task_id", "patch_hash", "base_hash"):
            value = event["attrs"].get(key)
            if isinstance(value, str):
                token = (key, value)
                mappings.setdefault(token, canonical_digest({"salt": salt, "key": key, "value": value}))
                event["attrs"][key] = mappings[token]
    document["run_id"] = "remapped-" + canonical_digest({"salt": salt, "run": trace.run_id})[:24]
    return Trace.from_dict(document)


def _sever_one_equality(trace: Trace, salt: int) -> Trace | None:
    document = trace.to_dict()
    positions: dict[str, list[int]] = {}
    for index, event in enumerate(document["events"]):
        value = event["attrs"].get("patch_hash")
        if isinstance(value, str):
            positions.setdefault(value, []).append(index)
    repeated = sorted((value, indexes) for value, indexes in positions.items() if len(indexes) >= 2)
    if not repeated:
        return None
    _, indexes = repeated[0]
    document["events"][indexes[-1]]["attrs"]["patch_hash"] = canonical_digest(
        {"severed": True, "salt": salt, "run": trace.run_id}
    )
    return Trace.from_dict(document)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--seed", type=int, default=404)
    args = parser.parse_args()
    corpus = load_frozen_corpus()
    if not 1 <= args.samples <= len(corpus.examples):
        raise ValueError("sample count is outside corpus bounds")
    rng = random.Random(args.seed)
    selected = rng.sample(list(corpus.examples), args.samples)
    comparisons = 0
    mismatches = 0
    endpoint_checks = 0
    endpoint_failures = 0
    for index, example in enumerate(selected):
        original_features = _signature(example.trace)
        original_evaluation = _evaluation_signature(example.trace)
        variants = (
            *nuisance_variants(example.trace),
            trace_from_otlp(trace_to_otlp(example.trace)),
            _remap_identities(example.trace, args.seed + index),
        )
        for variant in variants:
            comparisons += 2
            mismatches += int(_signature(variant) != original_features)
            mismatches += int(_evaluation_signature(variant) != original_evaluation)
        severed = _sever_one_equality(example.trace, args.seed + index)
        if severed is not None:
            endpoint_checks += 1
            endpoint_failures += int(sequence_features(severed) == sequence_features(example.trace))
    verdict = "PASS" if mismatches == 0 and endpoint_failures == 0 and endpoint_checks else "FAIL"
    result = {
        "schema": "rcdl.randomized-pressure-probe/0.4",
        "verdict": verdict,
        "seed": args.seed,
        "samples": args.samples,
        "comparisons": comparisons,
        "mismatch_count": mismatches,
        "endpoint_checks": endpoint_checks,
        "endpoint_failures": endpoint_failures,
        "identity_values_remapped": True,
        "nuisance_variants_per_sample": 5,
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

