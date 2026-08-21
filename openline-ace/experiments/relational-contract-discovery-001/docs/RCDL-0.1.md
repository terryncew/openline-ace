# RCDL 0.1

## Status

RCDL 0.1 is an experimental, bounded clause language. Its purpose is to make
candidate relations enumerable, monitorable, and intervention-addressable. It
is not a general temporal logic and does not claim completeness.

## Canonical representation

The machine authority is JSON restricted to null, booleans, signed 64-bit
integers, NFC strings, arrays, and string-keyed objects. Floats are forbidden.
Objects are serialized with lexicographically sorted keys, no insignificant
whitespace, UTF-8 encoding, and one trailing newline at the file boundary.

This restricted representation is deterministic for RCDL documents. It should
not be described as full RFC 8785 support.

## Clause closure

Every clause contains exactly:

- `schema`: `rcdl.clause/0.1`
- `id`: stable identifier
- `kind`: `guard`, `integrity`, `order`, or `progress`
- `trigger`: event kind plus at most six scalar predicates
- `require`: one bounded operation
- `intervention`: active hook, active strategy, sham strategy, and energy
- optional `description`

Unknown fields are rejected. A clause without an addressable intervention may
be monitored elsewhere, but it cannot enter the causal-standing pipeline.

## Operators

### `unique_per_key`

For all trigger events sharing the declared key tuple, the declared value tuple
must be identical.

### `exists_before`

For each trigger, a matching predecessor event must occur at a lower logical
step. Candidate-to-trigger joins are equality joins over at most four fields.

### `count_distinct_before`

For each trigger, distinct matching predecessors must meet a positive constant
or strict-majority threshold. Majority is computed as `floor(n / 2) + 1` from
declared trace metadata.

### `precedes_without`

A matching predecessor must exist and no matching blocker may occur between the
latest predecessor and the trigger.

### `eventually_within`

Under explicitly true trace assumptions, a matching event must occur within a
positive, finite logical-step horizon. This is bounded progress, not unqualified
liveness.

## Search bounds

- At most four fields in a join or grouping key.
- At most six scalar trigger predicates.
- At most one requirement operator per clause.
- No recursion, embeddings, free text predicates, floating point, arbitrary
  arithmetic, or unbounded negation.
- The official oracle result and post-hoc failure labels are not trace fields
  and are unavailable to candidate evaluation. The validator explicitly
  rejects oracle, verdict, standing, and intervention-label field names.

## Standing

In the Raft calibration a candidate is `SUPPORTED` only when:

1. it has no violation across successful baselines and meets the declared
   aggregate positive-support floor;
2. its active intervention violates the clause and an independent safety
   property in every declared trial;
3. its matched sham violates neither;
4. node renaming, event-ID renumbering, and object-key reordering preserve the
   evaluation;
5. the result repeats on held-out seeds; and
6. at least one inclusion-minimal supported family preserves the complete
   declared safety regime.

Standing is local to the clause grammar, implementation, oracle, scenarios,
and intervention policy recorded in the manifest.

The calibration also contains a frozen spurious observational control. It
holds throughout successful baselines and is therefore proposed by the miner.
Its targeted removal breaks the clause while preserving every declared Raft
safety property, so the Auditor records it as
`REJECTED_CAUSALLY_IRRELEVANT`. This is the calibration witness that proposal
and standing are separate authorities.

## Raft boundary

The calibration checks election safety, leader completeness, log matching, and
state-machine safety. Safety failures are prefix-closed: restoring a guard does
not erase a violation already present in history. Recovery is therefore not an
admissible criterion for these clauses. Bounded recovery belongs in a separate
progress campaign with explicit availability and fairness assumptions.
