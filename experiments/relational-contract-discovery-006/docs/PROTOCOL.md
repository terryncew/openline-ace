# RCDL-006 frozen protocol

Status: frozen before final evaluation  
Experiment: `relational-contract-discovery-006`  
Authority: `NONE`

## Question

Can an equal-budget relational-contract instrument distinguish a relationship
that the original verifier independently needs from a requirement that an
EnvHarness wrapper merely imposes?

The pilot clause is:

> Successful submission requires fresh test evidence bound to the current
> patch hash.

## Roles and authority

| Component | Permitted role | Scientific authority |
| --- | --- | --- |
| EnvRigger-shaped fixture | Propose an opaque candidate and mechanism | None |
| EnvHarness `Rules` | Apply active, sham, or restoration transformations | None |
| Original code-repair verifier | Judge submission and artifact validity | Sole oracle |
| Symbolic RCDL | Classify the three-query transcript | None |
| Learned baseline | Classify the same transcript | None |
| Receipt Gate | Attach verified evidence after freezing | No promotion authority |

The wrapper never modifies the verifier. A wrapper failure with a valid
artifact is evidence of an imposed rule, not evidence that the external
behavior required that rule.

## Upstream source boundary

The experiment imports actual source from
`https://github.com/google-research/envharness` at commit
`fab7d57441f06b75c73a900e04561d4d7600f361`.

Five core source files are hash-pinned in
`references/envharness-upstream.json`. Evaluation fails if the path set,
content hashes, or required `ActionableEnv`/`Rules` methods change.

The pilot does not invoke EnvRigger's LLM. It does not compile generated Python.
Mechanisms are static `Rules` subclasses selected by frozen opaque proposal
digests. This isolates the held-out-mechanism question from model and code-
generation nondeterminism.

## External behavioral oracle

The environment has two patch candidates. Only one is correct. The original
verifier returns success exactly when:

1. a submission occurred; and
2. the submitted current patch is the correct patch.

The verifier does not inspect test history, wrapper state, clause identifiers,
proposal identifiers, policy decisions, or receipts. A correct patch can be
submitted without running tests in the unwrapped environment. A unit test locks
that fact.

## Arms

Every case executes exactly three queries.

1. **Active:** enact the proposed mechanism.
2. **Matched sham:** exercise the same declared hook and payload-energy bucket
   while preserving the causal relation.
3. **Restoration:** restore or supply the candidate relation and measure the
   recovery horizon.

Active and sham energy objects must be byte-for-byte equal. An energy object
contains hook calls, logical mutation sites, payload-size bucket, and synthetic
delay. Any mismatch invalidates the tournament.

## Mechanism split

Development mechanisms:

- native: `stale-result`, `wrong-pass-cache`;
- wrapper-imposed: `submit-block`, `submit-rewrite`;
- nuisance: `surface-case`, `metadata-sort`.

Held-out mechanisms:

- native: `delayed-result`, `forged-lineage`;
- wrapper-imposed: `submit-shadow`, `submit-timeout`;
- nuisance: `role-rename`, `field-order`, `payload-padding`.

Every evaluation proposal is a two-layer composition. No evaluation operator
appears in development. The evaluation set contains two native, two imposed,
and two nuisance compositions.

## Agents and tasks

Development uses `direct-v1` on three development tasks. Evaluation uses
sixteen new task identities and two separately implemented policies:

- `ledger-v2`, which records observations in a ledger;
- `queue-v2`, which executes a queued action plan.

The implementations share the original verifier and action semantics but take
different control-flow paths. Transport requires identical causal signatures
and decisions across both implementations.

## Policy inputs and budgets

Both classifiers receive only the active, sham, and restoration outcomes plus
the measured recovery horizon. Neither receives the mechanism layer names,
proposal ID, oracle label, initial-condition label, or raw oracle model.

The observable signature is:

`(active success, active artifact valid, sham success, restoration success, recovery horizon)`

The symbolic rule classifies:

| Signature class | Standing |
| --- | --- |
| Active fails, artifact invalid, sham/restoration succeed | `SUPPORTED_NATIVE` |
| Active fails, artifact valid, sham/restoration succeed | `REJECTED_IMPOSED` |
| Active succeeds, artifact valid, horizon zero | `REJECTED_NUISANCE` |
| Failed sham, failed restoration, or undeclared pattern | `INVALID` |

The learned baseline receives development signatures with official labels and
learns a lookup over only the observable signature. It has the same three-query
evaluation budget.

## Frozen validity criteria

The result is valid only if all conditions hold:

- upstream source surface verifies;
- 384 evaluation records are emitted;
- each policy has 192 records;
- every case uses exactly three queries;
- active and sham energy match;
- sham failure count is zero;
- every restoration succeeds;
- recovery horizons are predicted exactly;
- decisions transport across both held-out agents;
- the manifest, result JSONL, and projection digest-bind each other.

## Verdict logic

Accuracy is measured in parts per million. A symbolic advantage requires an
accuracy lead of at least 100,000 ppm. An absolute difference below that margin
is parity. The code computes the verdict from final rows; fixture files do not
contain the final verdict.

## Frozen result

The observed result is `HELD_OUT_MECHANISM_CAUSAL_PARITY`.

- symbolic RCDL: 192/192 standings and 192/192 recovery horizons;
- learned baseline: 192/192 standings and 192/192 recovery horizons;
- decision distribution per policy: 64 native, 64 imposed, 64 nuisance;
- matched-sham failures: zero;
- agent transport: passed;
- unique symbolic advantage: not found.

## Falsifiers and reopening conditions

Quarantine or reopen the result if:

- any upstream pinned source hash changes;
- the original verifier begins checking wrapper-generated requirements;
- proposal labels or operator identities enter policy inputs;
- a held-out operator appears in development;
- a sham causes external failure;
- active/sham energy differs;
- restoration or transport fails;
- a bound artifact changes without its digest changing;
- independent replication or stochastic-agent transport disagrees.

## Limitations

This is a same-builder deterministic synthetic pilot. It uses the real
EnvHarness core but not live EnvRigger generation. It has one external verifier,
one clause family, no stochastic LLM agents, no independent team, and no
external preregistration. It establishes an executable boundary test, not a
general scientific law.
