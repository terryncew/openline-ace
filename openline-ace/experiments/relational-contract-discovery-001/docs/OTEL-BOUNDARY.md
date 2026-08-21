# OpenTelemetry boundary

RCDL 0.1 accepts the OpenTelemetry Protocol JSON encoding and normalizes it to
`rcdl.trace/0.1`. The adapter intentionally supports a small scalar profile so
that the clause engine receives deterministic data.

## Required mapping

| OTLP location | RCDL meaning |
|---|---|
| resource attribute `rcdl.run_id` | one non-empty run identifier |
| resource attribute `rcdl.meta.<field>` | trace metadata |
| span attribute `rcdl.node` | emitting actor or node |
| span attribute `rcdl.event.kind` | event kind; span name is the fallback |
| span attribute `rcdl.attr.<field>` | event attribute |
| span `spanId` | opaque event identifier |
| span `startTimeUnixNano` | primary ordering key |

Exactly one run ID may appear in a normalized document. Spans are ordered by
`(startTimeUnixNano, spanId)` and assigned strictly increasing logical steps.
Duplicate attribute keys, invalid integers, arrays, bytes, doubles, and nested
values fail closed. Supported values are strings, booleans, and signed 64-bit
integers.

Outcome and intervention labels remain outside the discovery feature space.
RCDL clause validation rejects fields such as `oracle_passed`, `verdict`,
`standing`, `arm`, and `hook`; the independent oracle consumes its own trace
view after candidate proposal.

## Normalize

```bash
python3 -m rcdl ingest-otel input.otlp.json normalized-trace.json
```

The adapter is a boundary converter, not an OpenTelemetry collector or storage
backend.
