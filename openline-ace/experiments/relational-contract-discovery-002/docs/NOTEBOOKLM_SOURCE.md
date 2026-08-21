# Relational Contract Discovery: study source

Status date: 2026-08-21

Project: OpenLine ACE, experiments RCDL-001 and RCDL-002

Standing: falsifiable engineering program; ACE Level 1 Candidate; no policy authority

This document is designed to be uploaded to NotebookLM as one self-contained
source. It explains the research question, intellectual lineage, implemented
instrument, current evidence, limits, and next experiments. Repository files
remain the primary source for exact executable details.

## The shortest accurate explanation

Relational Contract Discovery (RCDL) is an experimental instrument that starts
with successful execution traces, proposes candidate relationships from a
small predeclared grammar, deliberately breaks each relationship, compares the
break with a matched sham, asks an independently represented external oracle
whether behavior failed, and reduces the survivors to inclusion-minimal
contract families.

It is not a coherence score, a theory of everything, proof that a system has an
essence, or an authority engine. It is a causal-testing harness for a bounded
hypothesis space.

The research object is:

> Discover the family of inclusion-minimal relational contracts that preserve
> a predeclared external behavior under a defined perturbation regime.

## How the question changed

The motivating intuition was that a system may remain recognizably the same
because some relationships persist through change. The early phrasing—find the
smallest constraints that make a system “remain itself”—was not falsifiable.
“Itself” could be redefined after every result, and “the smallest set” assumed
there was one unique mechanism.

The engineering correction makes four commitments:

1. Identity means agreement with an external behavioral specification, not an
   internal feeling of coherence.
2. The perturbation regime is declared before evaluation.
3. More than one incomparable minimal contract family may exist.
4. A rule earns local standing only through interventions, recovery, held-out
   checks, nuisance invariance, and minimality—not because it was frequent.

This is the boundary between a testable instrument and metaphysics.

## Intellectual lineage: what is inherited and what is new

The high-level idea is not novel. RCDL combines established ideas and tests a
narrower potential contribution: automating candidate rule proposal and
hostile causal testing while keeping the proposer unable to certify itself.

### Computation as organisation

Kimia Witte's 2026 preprint, *Computation as Organisation*, defines
organisation in terms of persistent relational constraints and frames
persistence, recovery, and structural failure under perturbation as
experimentally accessible criteria. This is the closest high-level precursor.
RCDL does not claim that philosophical framework as a discovery. It converts a
small part of the intuition into an executable, falsifiable workflow.

Source: https://arxiv.org/abs/2601.11599

### Computational mechanics

Computational mechanics groups histories that have the same predictive future
into causal states and studies minimal predictive representations. It supplies
important precedent for defining structure through predictive equivalence and
minimality. RCDL is different: it tests trace-level relational clauses with
explicit interventions and an external behavior oracle.

Source: https://arxiv.org/abs/cond-mat/9907176

### Bisimulation and behavioral equivalence

Bisimulation formalizes when systems with different internal states or
realizations match one another behaviorally. It supplies precedent for
grounding “same system” in observable behavior rather than identical internal
implementation. RCDL-001 and RCDL-002 do not implement or prove formal
bisimulation; their test oracles are finite operational approximations.

Source: https://doi.org/10.1109/TAC.2004.838497

### Assume/guarantee contracts

Contract theory specifies what a component assumes about its environment and
what it guarantees in return. It supplies a mature language for modular system
specifications and refinement. RCDL's distinct question is whether a bounded
instrument can propose candidate relational clauses from behavior and then
test which ones are interventionally necessary.

Source: https://arxiv.org/abs/2012.12657

### Causal representation learning

Causal representation learning asks how high-level causal variables might be
discovered from lower-level observations and emphasizes interventions,
generalization, and the difficulty of assuming the right variables are already
given. RCDL does not solve causal representation learning: its event vocabulary
and actuator map are domain supplied.

Source: https://doi.org/10.1109/JPROC.2021.3058954

### Non-unique mechanisms

*All Circuits Lead to Rome* reports structurally different sparse circuits that
can support the same model behavior. Whether or not those findings transport
outside the paper's setting, they directly warn against assuming a unique
smallest mechanism. RCDL therefore returns a family of inclusion-minimal
contract sets rather than one privileged invariant.

Source: https://arxiv.org/abs/2605.12671

### Representation dependence

*Intrinsic Structure* distinguishes coordinate-independent identifiable
fingerprints from human-legible decompositions and argues that circuit outputs
can reflect the discovery method. This motivates RCDL's nuisance controls, but
those controls are modest: actor renaming, event-ID renumbering, object-key
reordering, and OTLP round trips do not prove general coordinate independence.

Source: https://arxiv.org/abs/2608.10172

### Negative evidence

The 2026 Zenodo record *From Relational Invariants to Spectral
Reconstructibility* reports that increasingly elaborate neural relational
invariants did not reliably improve recovery prediction or cross-dataset
transport. Its reported exact gain-invariant construction improved held-out
macro AUROC by 0.0131, worsened log loss, and was not significant. This is a
useful falsification warning: changing a scalar into a relation does not make it
causal or transportable. Treat this as a recent research record, not settled
consensus or independent validation of RCDL.

Source: https://zenodo.org/records/21875043

### Nearby agent-workflow benchmarks

WorkflowPerturb studies metric behavior over controlled perturbations of golden
workflows. ForestBench maps heterogeneous multi-agent traces into unified
collaboration graphs and uses multiple successful reference graphs. These make
generic workflow stress testing or graph scoring a poor novelty claim for
RCDL. The narrower opening is causal testing of minimal contract families,
recovery prediction, and transport.

Sources:

- https://arxiv.org/abs/2602.17990
- https://arxiv.org/abs/2608.08605

## The closed-loop instrument

```text
execution traces
      |
      v
bounded candidate miner
      |
      v
active intervention  <-->  matched sham
      |                       |
      +----------+------------+
                 v
      independent behavior oracle
                 |
                 v
   held-out + nuisance + recovery checks
                 |
                 v
 inclusion-minimal contract families
                 |
                 v
 evidence-only ACE projection; no authority
```

The separation of roles is essential:

- The Explorer may propose clauses from trace support.
- The Auditor controls active and sham mutations.
- The Oracle judges declared external behavior from a separate outcome object.
- The reducer asks whether a proper subset works just as well.
- The projection carries bounded evidence but cannot grant authorization.

If the miner sees oracle labels, or the projection can promote itself, the
experiment is invalid even if every metric is high.

## The frozen clause language

RCDL 0.1 deliberately avoids arbitrary first-order logic. Each JSON clause has
a trigger, one requirement, and an actionable active/sham intervention record.
The finite operators are:

- `unique_per_key`: a value may not conflict within a declared key;
- `exists_before`: a matching event must already exist;
- `count_distinct_before`: enough distinct matching events must exist;
- `precedes_without`: a matching event must precede the trigger without an
  intervening blocker; and
- `eventually_within`: a matching event must occur within a logical-step
  horizon when declared assumptions hold.

This grammar can express provenance, state conditioning, order/exclusion, and
bounded progress. It does not express arbitrary logical programs. Candidate
proposal in the current releases is finite-domain support filtering, not
open-ended ILP synthesis.

## Why active-versus-sham matters

Suppose a proposed clause says that a test result must refer to the current
patch hash.

- Active arm: bypass the identity guard so stale passing evidence is presented
  as if it belongs to the current broken patch.
- Sham arm: emit a structurally matched metadata no-op while preserving the
  identity guard.
- Oracle: independently checks release correctness, hidden tests, side effects,
  current evidence, and approval safety.

The clause receives local support only when its active removal breaks both the
clause and external behavior, while the sham preserves both. A planted rule can
be common in every successful trace and still be rejected if removing it does
not hurt external behavior.

The current energy match is one structural intervention event in each arm. It
does not establish equal token degradation, latency, semantic shock, or prompt
disruption for LLM systems.

## RCDL-001: Raft calibration

RCDL-001 is the answer-key calibration. It uses a deterministic three-node Raft
micro-harness, six declared safety candidates, and one planted audit-marker
control. The independent oracle checks election safety, leader completeness,
log matching, and state-machine safety.

Its frozen receipt reports:

- 32 trials per arm;
- six locally supported clauses;
- one causally rejected spurious control;
- one minimal family;
- 57 unit tests; and
- 28,000 randomized comparisons with zero recorded mismatches.

The official Ongaro Raft TLA+ file is pinned by identity, but the repository
does not run TLC and has no machine-checked refinement mapping between the
micro-harness and official model. Therefore the correct claim is local
calibration only—not rediscovery of formally proven Raft invariants.

Repository path: `experiments/relational-contract-discovery-001/`

Raft background: https://raft.github.io/

## RCDL-002: deterministic repair-workflow transport

RCDL-002 asks whether the exact RCDL 0.1 engine can be reused in a different
deterministic domain without changing its parser, evaluator, miner, nuisance
transforms, reducer, trace model, canonical serializer, or OTLP adapter.

The substrate is a rule-based workflow:

```text
planner -> implementer -> tester -> reviewer -> release decision
```

There are no LLMs, API calls, prompt variants, or live tools. The workflow is a
controlled second rung between Raft and stochastic agents.

The four target clauses are:

1. a passing test result must derive from a run on the claimed patch;
2. approval must follow inspection of the current patch;
3. approval must follow a passing required-suite result for that patch; and
4. recovery after failure requires a fresh observation within three logical
   steps when recovery is available.

The planted control says a planner-to-reviewer note is required. It appears in
successful traces but must be rejected because its removal has no independent
effect on external behavior.

The external oracle is not serialized into the trace. It separately checks:

- correct release decision;
- hidden-test success for released artifacts;
- absence of forbidden side effects;
- test and review evidence matching the released patch;
- no approval on a known failing test result; and
- fresh-observation recovery within the declared horizon.

The frozen release target is 32 trials per arm, four supported targets, one
rejected control, one four-clause minimal family, and a 1,000-seed randomized
probe. Exact results and digests live under
`experiments/relational-contract-discovery-002/evidence/`; the files must be
verified rather than trusted from this prose.

Repository path: `experiments/relational-contract-discovery-002/`

## What is automated

For these deterministic calibrations, trace generation, candidate filtering,
active/sham execution, oracle evaluation, family reduction, held-out seeds,
nuisance transforms, OTLP normalization, manifest generation, projection
generation, randomized probes, and evidence verification are automated.

GitHub Actions reruns the checks after relevant pushes and pull requests.
There is no continuously running monitor and nothing to collect manually for
RCDL-002. A production system would still need live trace ingestion, privacy
and retention policy, actuator authorization, scheduling, alerting, and a human
response process. Those capabilities are not implied by green CI.

## How to reproduce RCDL-002

From the repository root:

```bash
cd experiments/relational-contract-discovery-002
export PYTHONPATH="../relational-contract-discovery-001:."

python3 -m unittest discover -s tests -v
python3 -m rcdl002 verify-engine
python3 -m rcdl002 verify-evidence

python3 -m rcdl002 calibrate --output calibration-out --trials 8
python3 -m rcdl002 verify-manifest calibration-out/contract-manifest.json
python3 -m rcdl002 verify-projection calibration-out/contract-projection.json
python3 scripts/randomized_probe.py --seeds 64
```

`verify-engine` proves only that the selected engine files match the pinned
digests. `verify-evidence` checks canonical bytes, sidecars, source binding, and
evidence closure. Neither command creates independent scientific replication.

## How to read the outputs

`contract-manifest.json` is the detailed result. For each clause, inspect:

- baseline support;
- active and sham clause-failure rates;
- active and sham external-oracle failure rates;
- held-out outcomes;
- nuisance and OTLP checks;
- standing and reason; and
- membership in a minimal family.

`contract-projection.json` is a deliberately smaller handoff for Receipt Gate
and Claim Graph. It must say:

- ACE level `1_CANDIDATE`;
- authorization `NONE`;
- receiver must reverify;
- evidence attachment is eligible;
- policy input is not eligible; and
- standing is limited to local deterministic transport.

`experiment-receipt.json` binds the claim, evidence pointers, result boundary,
and next-use limitation. `evidence-index.json` closes the evidence file set.
Signatures or hashes are identity and tamper evidence, not proof that the claim
is scientifically valid.

## What would falsify the current program

RCDL-002 fails if any of the following occurs:

- a target active arm does not fail more than its sham;
- the planted note is promoted;
- oracle values leak into discovery traces;
- harmless actor, event-ID, representation, or OTLP changes alter evaluation;
- a proper subset preserves all declared scenarios;
- the fresh observation arrives after the horizon but is reported as recovery;
- held-out deterministic seeds reverse the result;
- the experiment needs modified RCDL 0.1 semantics; or
- a rehashed artifact can grant itself policy authority.

The larger research program should be considered unsuccessful if frozen
contract families do not beat ordinary predictive baselines, do not transport
to independent implementations and model swaps, or collapse under realistic
nuisance changes.

## What has not been proved

Neither calibration establishes:

- open-ended automated rule synthesis;
- completeness of the clause vocabulary;
- formal bisimulation;
- uniqueness of the contract family;
- cross-implementation transport;
- stochastic LLM-workflow validity;
- token-, timing-, and semantic-shock-matched shams;
- superiority to full-trace classifiers and ordinary metrics;
- a live monitoring or enforcement product;
- safety of automatically mutating production workflows; or
- a general law of biological, social, or computational organisation.

These are explicit blockers, not footnotes.

## The calibration ladder

1. RCDL-001: deterministic Raft micro-harness with known local answer keys.
2. RCDL-002: deterministic rule-based repair workflow using the frozen engine.
3. Next: an independently implemented deterministic workflow and ordinary
   predictive baselines.
4. Later: stochastic planner/implementer/tester/reviewer agents, realistic
   prompt and tool perturbations, model swaps, and token/timing-matched shams.
5. Only after transport: consider evidence-only integration with production
   trace systems; enforcement requires separate policy and authorization.

The next experiment should not skip directly to brains or institutions. Their
boundaries, interventions, and ground truth are too ambiguous for early
instrument validation.

## Questions for self-study

1. Why is “behavioral equivalence under a declared oracle” more falsifiable
   than “the system remains itself”?
2. Why can there be multiple inclusion-minimal contract families?
3. What information must be unavailable to the miner?
4. What causal mistake does the planted planner-note rule expose?
5. Why does a targeted active arm need a sham arm?
6. What does structural energy 1 fail to control in an LLM workflow?
7. Why is a pinned TLA+ file not the same as executing a formal model?
8. What exactly transported from RCDL-001 to RCDL-002?
9. Why does bounded recovery require a declared fairness assumption?
10. What evidence would justify moving from ACE Level 1 to a stronger claim?

## One-paragraph answer to remember

We are building a falsification instrument, not a universal coherence theory.
It proposes a finite set of relational rules from successful traces, attacks
each with a targeted intervention and a matched sham, lets a separately
represented behavior oracle decide whether the system failed, tests recovery
and nuisance invariance, and returns inclusion-minimal families with bounded
standing. RCDL-001 calibrated that loop locally on Raft; RCDL-002 tests whether
the frozen engine works unchanged on a deterministic code-repair workflow.
Passing supports only local deterministic transport. The decisive future test
is whether frozen contracts predict failure and recovery across independent
implementations and stochastic model swaps better than ordinary baselines.
