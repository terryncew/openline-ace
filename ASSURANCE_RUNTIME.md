# Assurance Runtime

> AI makes generating complex code cheap; the Assurance Runtime prevents the generator from controlling the evidence, authority, or standing that determines whether its output may run.

**Canonical invariant:** capability may propose reliance. It cannot confer reliance on itself.

The Assurance Runtime is a structural membrane between generation and consequential reliance. It is not an agent framework, a model safety claim, or a correctness oracle. It composes independent evidence, principal-bound authority, receiver-side admission, and reversible standing at the boundary where a proposed state becomes relied upon.

The reference transition is:

```text
GENERATE
  -> INDEPENDENTLY EVALUATE
  -> TEST CONSEQUENCES
  -> CHECK AUTHORITY
  -> RECEIVER GATE
  -> PROMOTE / EXECUTE
  -> BIND RECEIPT
  -> RETAIN CAUSAL DEPENDENCIES
  -> REOPEN IF STANDING CHANGES
```

The contracts below are normative. Implementations may change internal code, cryptographic primitives, storage, evaluator technology, or orchestration as long as these boundaries do not collapse.

## 1. Generator Gate contract

**Purpose:** prevent the system that searches for improvement from controlling the evidence that declares generator-level improvement real.

### Mutation tiers

| Tier | Surface | Required treatment |
| --- | --- | --- |
| Tier 1 — Operational | ordinary implementation changes inside the principal-authorized work scope | task evidence + consequence evidence + mandate |
| Tier 2 — Generator | search strategy, retrieval, routing, candidate generation, persistent proposal-shaping configuration | Tier 1 evidence plus a structurally separate meta-evaluator |
| Tier 3 — Constitutional | tests, protected evaluators, gate policy, mandate policy, receipt verification, standing rules, or the definition of success | outside agent mutation authority |

Unknown or ambiguous persistent proposal-shaping surfaces default upward. A generator-level effect may not be laundered through the Tier 1 lane by changing filenames or import structure.

### Evaluator separation

A Tier 2 proposal MUST NOT be promoted on evidence issued by the generator being judged. The protected meta/progress evaluator MUST be principal-owned or independently sourced and MUST be unavailable for adaptive querying during the search that produced the candidate. Acceptance/rejection feedback MUST NOT become an unlimited reusable-holdout oracle.

RGG-001 showed that evaluator capture can emerge under ordinary optimization pressure when the generator and its definition of progress collapse into one channel. RGG-002 showed that a separated binary Generator Gate could eliminate observed capture while preserving independently measured genuine progress on the frozen reference substrate.

## 2. Mandate & Policy Gate contract

**Purpose:** keep demonstrated capability separate from execution authority.

A proposal MUST identify at least:

```text
proposal_id
actor_id
parent_state_hash
payload_hash
action
changed_paths / changed_symbols
mutation_tier
```

The receiver MUST require authenticated, principal-bound mandate evidence for the exact consequential action. A valid mandate SHOULD bind:

- principal and authorized actor;
- permitted action class;
- permitted path / symbol / resource scope;
- temporal validity and freshness requirements;
- optional spend, tool, network, or execution ceilings;
- successor / revocation state when applicable.

The current research implementation uses signed, receiver-verifiable receipt records. Production implementations may substitute another cryptographic credential system, but a peer message, agent-authored approval, persuasive PR text, or self-issued receipt MUST NOT satisfy the authority slot.

The agent MUST NOT be able to expand its own authorized scope by introducing a new dependency edge. Unregistered or dynamically unresolved edges require conservative consequence expansion, quarantine, or denial.

## 3. Receipt Gate contract

**Purpose:** decide at the receiver's consequential boundary whether the exact proposal has earned current standing.

Local viability is evidence, not authority. Passing a target test is insufficient for promotion.

For an ordinary operational proposal, the receiver MUST verify evidence for the exact payload including:

1. task viability or target improvement;
2. non-regression / consequence evaluation over the frozen affected scope;
3. a current principal mandate;
4. subject and state binding;
5. issuer-role separation;
6. evidence freshness / current standing.

Tier 2 proposals additionally require Generator Gate evidence.

The canonical dispositions are:

```text
COMMIT      evidence and authority satisfy the receiver's current policy
QUARANTINE  evidence is incomplete or standing is insufficient for reliance
DENY        the proposal violates a frozen boundary or fails required evidence
```

### Consequence closure

For code promotion, evaluation MUST cover the principal-owned affected-scope closure rather than only the textual diff. A change to a shared symbol requires regression checking of its frozen downstream consumers. Newly introduced or unresolved dependency edges MUST NOT shrink that closure.

FAR-006 demonstrated the point on an independently authored Flask task: the overbroad candidate passed the new target but caused **43 failures** in the pinned consequence suite and was denied, while the historical repair passed the target and all 60 consequence tests and was admitted.

### Promotion receipt

A consequential promotion SHOULD bind:

```text
source_state_hash
promoted_state_hash
candidate_hash
evidence_receipt_ids
mandate_receipt_id
gate_decision
dependency_receipt_ids
standing_at_promotion
```

A receipt proves what the receiver relied on. It does not grant itself permanent standing.

## 4. Claim Graph & Frame Ledger contract

**Purpose:** preserve the causal evidence closure of relied-upon states so later standing changes have precise consequences.

The graph MUST distinguish chronology from causal dependency. A later promotion does not automatically depend on every earlier receipt. An edge exists only when the downstream state or its admissibility relied on the upstream evidence.

At minimum the standing model must support these semantics:

| State / disposition | Meaning |
| --- | --- |
| `ACTIVE` / `RETAIN` | current reliance remains supported |
| `REVOKED` | the referenced authority or evidence has explicitly lost standing |
| `REOPEN` | an accepted downstream state depended on evidence that lost standing and must be reconsidered |
| `QUARANTINE` | present but lacking authority for consequential reliance |
| `DENY` | receiver refuses the proposed consequential transition |

When an upstream receipt loses standing, the receiver MUST identify the causally affected descendants, reopen them, and preserve unrelated nodes. Historical execution MUST NOT make a decision permanently legitimate.

FAR-005 exercised causal dependency binding and selective reopening on a dependency-linked reference repository. FAR-006 repeated the standing transition on external code: after the external oracle was revoked, the promoted Flask fix and main-reliance node became `REOPEN`, an unrelated license record remained `ACTIVE`, and reliance on the reopened main state was denied.

## Integration boundary

An operator adopting the Assurance Runtime owns the authority and the definition of success. OpenLine is not a central authority.

The operator supplies:

- the principal / mandate authority;
- protected evaluator and test surfaces;
- the consequence suite;
- the affected-scope resolver;
- standing / revocation inputs;
- the receiver boundary that turns a proposal into relied-upon state;
- receipt persistence and causal dependency storage.

The generator may propose changes continuously. Consequential state changes occur only at discrete receiver-owned admission boundaries.

A minimal integration exposes these logical records:

```text
Proposal
EvidenceReceipt
MandateReceipt
GateDecision
PromotionReceipt
StandingEvent
```

The wire format is intentionally unspecified here. Interoperability depends on the invariant bindings, not on one vendor's object model.

## Threat model

The reference runtime is designed to resist, within declared closures:

- generator self-evaluation and definition-of-success mutation;
- manufactured mandate evidence and peer-agent "GO" messages;
- self-issued or subject-mismatched receipts;
- local-test success hiding a known downstream regression;
- unauthorized path / dependency / workflow edits;
- generator-level changes routed through an ordinary patch lane;
- continued reliance after a causally required evidence receipt loses standing.

An independent deployment should specifically stress:

**Flaky and nondeterministic evidence.** A one-off green run SHOULD NOT silently become authoritative evidence when the harness is known to be unstable. Operators should define reproducibility policy, retry budgets, confidence rules, and a quarantine state before deployment.

**Dynamic-language reachability.** Reflection, monkey-patching, runtime imports, plugin loading, and environment-dependent edges can defeat static reachability. Unknown dynamic edges must expand checking, trigger runtime tracing, quarantine, or fail closed rather than disappear from the consequence closure.

**CI/CD friction.** Content-addressed evidence reuse and incremental consequence closures can reduce latency, but performance optimization MUST NOT allow an agent or merge queue to bypass receiver-side verification at the promotion boundary.

## Explicit non-claims

The Assurance Runtime does **not** establish:

- semantic optimality;
- correctness on unasserted or unknown edge cases;
- arbitrary-repository correctness;
- general coding-agent safety;
- complete dynamic-language dependency discovery;
- production filesystem capability confinement;
- distributed revocation correctness across arbitrary receivers;
- resistance to human social engineering;
- that the principal, receiver, or policy holder is benevolent or trustworthy;
- production-grade CI/CD latency or merge-queue integration.

The architecture is neutral scaffolding. It prevents an agent from granting itself authority it was not given; it cannot decide whether the legitimate holder of authority deserves that authority.

The empirical claim is narrower: **within the declared evidence, authority, scope, and standing closures, the generator does not control the facts that authorize consequential reliance on its own output.**

## Evidence chain

The FAR line is now frozen. Negative results remain part of the record; later experiments do not rewrite them.

| Artifact | Canonical location / commit | Standing in the evidence chain |
| --- | --- | --- |
| RGG-001 | `experiments/recursive-generator-governance-001/` — head `f6120af3f8a769320d1664a60528be9dae14e9ce` | Prospective negative. Unified evaluation produced capture; the original retention requirement failed. |
| RGG-002 | `experiments/recursive-generator-governance-002/` — head `4ddb29bbcbc7554c9c3a86f99f6a559b96e36dec` | Generator Gate supported under a fresh post-trajectory progress evaluator. |
| FAR-001 | `FAR-001.md`, `openline/fiduciary_agent_runtime.py` — head `fb7dcc770ec79f1d49eb811fb38f2ddfd2bf810a` | Mechanical composition of proposal, evidence, authority, standing, and consequence roles. |
| FAR-002 | `experiments/fiduciary-agent-runtime-002/` — head `b0b7351047df9a943d7a1bcc6da304c6da9ccb45` | Prospective negative; global admission floor created an absorbing progress deadlock. |
| FAR-003 | `experiments/fiduciary-agent-runtime-003/` — head `2253d9ca88c7830e550c131c6c246f77681aae77` | Prospective negative; raw commit-rate denominator penalized rapid saturation. |
| FAR-004 | `experiments/fiduciary-agent-runtime-004/` | Saturation-aware incremental admission supported on the reference coding substrate without changing FAR-003 runtime behavior. |
| FAR-005 | `experiments/fiduciary-agent-runtime-005/` — head `9831cdd1bb5f4447d1d9a2e1f3dce4fcd3aaa007` | Dependency-linked assurance, remote-regression rejection, causal receipt binding, and selective reopening supported on the reference repository. |
| FAR-006 | `experiments/fiduciary-agent-runtime-006/` — head `4205f59dd2d6c9375f9d0789f2a0ac4d79edf92f` | External promotion supported on pinned `SWE-bench_Verified` Flask task `pallets__flask-5014`. |
| Receipt Gate | `https://github.com/terryncew/openline-receipt-gate` | Receiver-owned verification / admission membrane that supplies the execution-boundary lineage. |
| Claim Graph / Frame Ledger | FAR-005 and FAR-006 standing graphs and recall traces | Causal dependency and selective `REOPEN` evidence used by the integrated runtime. |

### Canonical FAR-006 primary receipt

The permanent archive lives at:

`assurance-runtime/evidence/far-006/`

Canonical identifiers:

```text
FAR-006 verdict:
FIDUCIARY_RUNTIME_EXTERNAL_PROMOTION_SUPPORTED_ON_PINNED_FLASK_TASK

FAR-006 result.json SHA-256:
bb6acdaac8c7c0274659a2243016c3f9a9e3736ad939794ac584f76924f33de8

Original GitHub Actions artifact ZIP SHA-256:
781f00a4dc6cb082d626ffd9e6eb58341bc59b7fc7f1b7f211231f672680701b

Workflow run:
33339704659

Artifact ID:
9740150517

Primary ran against main:
c7c39282a332710c848a950709bf84d265e1e6f9
```

The original Actions ZIP and each extracted member are archived verbatim. `ARCHIVE_MANIFEST.json` binds their hashes and source run.

## FAR line closure

`FAR-001` through `FAR-006` are frozen as a closed research lineage.

There is **no FAR-007**.

Another OpenLine-authored fixture would add little independent evidence and risks benchmark recursion. The next honest challenge is an independent operator using the membrane on a repository, test/evaluation system, mandates, and promotion boundary they control. That work should use a distinct external-operator or interoperability track rather than extending the FAR numbering.

The next falsifier is therefore organizational as well as technical:

> Can an operator who did not design these experiments use the same membrane on their own consequential boundary without OpenLine controlling the repository, evaluator, mandate, or result?
