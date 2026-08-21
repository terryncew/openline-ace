"""Minimal OTLP JSON adapter for the RCDL normalized trace boundary."""

from __future__ import annotations

import hashlib
from typing import Any

from .trace import TRACE_SCHEMA, Trace


class OTelAdapterError(ValueError):
    pass


def _decode_any(value: Any) -> bool | int | str:
    if not isinstance(value, dict) or len(value) != 1:
        raise OTelAdapterError("OTLP AnyValue must contain exactly one supported field")
    if "stringValue" in value and isinstance(value["stringValue"], str):
        return value["stringValue"]
    if "boolValue" in value and isinstance(value["boolValue"], bool):
        return value["boolValue"]
    if "intValue" in value:
        raw = value["intValue"]
        if isinstance(raw, bool):
            raise OTelAdapterError("boolean is not an OTLP integer")
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str):
            try:
                return int(raw, 10)
            except ValueError as exc:
                raise OTelAdapterError("invalid OTLP integer string") from exc
    raise OTelAdapterError("only stringValue, boolValue, and intValue are supported")


def _encode_any(value: Any) -> dict[str, Any]:
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int):
        return {"intValue": str(value)}
    if isinstance(value, str):
        return {"stringValue": value}
    raise OTelAdapterError(f"unsupported OTLP scalar: {type(value).__name__}")


def _attributes(items: Any) -> dict[str, bool | int | str]:
    if not isinstance(items, list):
        raise OTelAdapterError("OTLP attributes must be an array")
    result: dict[str, bool | int | str] = {}
    for item in items:
        if not isinstance(item, dict) or set(item) != {"key", "value"}:
            raise OTelAdapterError("invalid OTLP attribute")
        key = item["key"]
        if not isinstance(key, str) or not key or key in result:
            raise OTelAdapterError("empty or duplicate OTLP attribute key")
        result[key] = _decode_any(item["value"])
    return result


def _attribute_array(values: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"key": key, "value": _encode_any(value)}
        for key, value in sorted(values.items())
    ]


def trace_from_otlp(document: dict[str, Any]) -> Trace:
    if not isinstance(document, dict) or set(document) != {"resourceSpans"}:
        raise OTelAdapterError("expected an OTLP JSON resourceSpans document")
    resource_spans = document["resourceSpans"]
    if not isinstance(resource_spans, list) or not resource_spans:
        raise OTelAdapterError("resourceSpans must be a non-empty array")

    normalized: list[tuple[int, str, str, str, dict[str, Any], str]] = []
    metadata: dict[str, Any] = {}
    run_ids: set[str] = set()
    for resource_span in resource_spans:
        if not isinstance(resource_span, dict):
            raise OTelAdapterError("resource span must be an object")
        resource = resource_span.get("resource", {})
        if not isinstance(resource, dict):
            raise OTelAdapterError("resource must be an object")
        resource_attrs = _attributes(resource.get("attributes", []))
        for key, value in resource_attrs.items():
            if key.startswith("rcdl.meta."):
                metadata[key.removeprefix("rcdl.meta.")] = value
        resource_run = resource_attrs.get("rcdl.run_id")
        scope_spans = resource_span.get("scopeSpans")
        if not isinstance(scope_spans, list):
            raise OTelAdapterError("scopeSpans must be an array")
        for scope_span in scope_spans:
            if not isinstance(scope_span, dict) or not isinstance(scope_span.get("spans"), list):
                raise OTelAdapterError("scope span must contain spans")
            for span in scope_span["spans"]:
                if not isinstance(span, dict):
                    raise OTelAdapterError("span must be an object")
                attrs = _attributes(span.get("attributes", []))
                run_id = attrs.pop("rcdl.run_id", resource_run)
                node = attrs.pop("rcdl.node", None)
                kind = attrs.pop("rcdl.event.kind", span.get("name"))
                span_id = span.get("spanId")
                raw_time = span.get("startTimeUnixNano")
                if not all(isinstance(item, str) and item for item in (run_id, node, kind, span_id)):
                    raise OTelAdapterError("span is missing RCDL identity attributes")
                try:
                    time = int(raw_time)
                except (TypeError, ValueError) as exc:
                    raise OTelAdapterError("invalid startTimeUnixNano") from exc
                extras = {
                    key.removeprefix("rcdl.attr."): value
                    for key, value in attrs.items()
                    if key.startswith("rcdl.attr.")
                }
                run_ids.add(run_id)
                normalized.append((time, span_id, node, kind, extras, run_id))
    if len(run_ids) != 1:
        raise OTelAdapterError("one normalized trace must contain exactly one run_id")
    normalized.sort(key=lambda item: (item[0], item[1]))
    run_id = next(iter(run_ids))
    events = [
        {
            "event_id": span_id,
            "step": step,
            "node": node,
            "kind": kind,
            "attrs": attrs,
        }
        for step, (_, span_id, node, kind, attrs, _) in enumerate(normalized)
    ]
    return Trace.from_dict(
        {
            "schema": TRACE_SCHEMA,
            "run_id": run_id,
            "metadata": metadata,
            "events": events,
        }
    )


def trace_to_otlp(trace: Trace) -> dict[str, Any]:
    resource_values = {"rcdl.run_id": trace.run_id}
    resource_values.update({f"rcdl.meta.{key}": value for key, value in trace.metadata.items()})
    spans = []
    for event in trace.events:
        span_id = hashlib.sha256(event.event_id.encode("utf-8")).hexdigest()[:16]
        values = {
            "rcdl.node": event.node,
            "rcdl.event.kind": event.kind,
        }
        values.update({f"rcdl.attr.{key}": value for key, value in event.attrs.items()})
        spans.append(
            {
                "traceId": hashlib.sha256(trace.run_id.encode("utf-8")).hexdigest()[:32],
                "spanId": span_id,
                "name": event.kind,
                "startTimeUnixNano": str(event.step + 1),
                "endTimeUnixNano": str(event.step + 1),
                "attributes": _attribute_array(values),
            }
        )
    return {
        "resourceSpans": [
            {
                "resource": {"attributes": _attribute_array(resource_values)},
                "scopeSpans": [
                    {
                        "scope": {"name": "openline-ace-rcdl", "version": "0.1"},
                        "spans": spans,
                    }
                ],
            }
        ]
    }

