# OpenLine Agent Contract Audit 002

A-002 is the **Blind External Stochastic Run Pack** for the contract microscope.

A-001 proved only that the active/sham/restoration mechanics can separate a
planted dependency from a planted ritual. A-002 freezes the next claim before a
provider run exists:

> Can an LLM proposer, denied hidden verifier state, surface candidate workflow
> dependencies from successful traces and can the frozen A-001 standing engine
> then separate at least one load-bearing dependency from at least one correlated
> ritual under real stochastic LLM execution?

The checked release does **not** answer that question. Its status is:

`PROTOCOL_CONFORMANCE_PASS_EXTERNAL_UNRUN`

Scientific standing:

`MECHANICS_ONLY_NOT_EXTERNAL_AGENT_EVIDENCE`

The live lane requires an external LLM provider. CI never substitutes a fixture
for that requirement.

## Boundary

- The proposer sees only successful baseline trace projections and public tool schema.
- Proposer output, compiler output, compiled candidates, and the full arm schedule are hash-sealed before targeted intervention begins.
- It never receives current/stale task secrets, verifier logic, expected standing, or hidden truth.
- An untrusted compiler maps open-text candidates onto a frozen public intervention catalog.
- The compiler cannot emit arbitrary executable code and cannot grade its own candidate.
- A-002 reuses A-001's frozen statistical standing engine and verifies its exact Git blob pins before import.
- The task verifier checks only whether the final output hashes to the current task token.
- A separate stdlib-only replay verifier recomputes every success bit from task bytes and final-output hashes.
- Contract manifests retain `policy_authority: NONE` and are not runtime permissions.

## Checked protocol conformance

The fixture exercises two candidates through the exact live result schema:

- `ticket.token_freshness` -> `SUPPORTED`;
- `ticket.audit_marker_presence` -> `REJECTED_RITUAL`.

That demonstrates protocol mechanics only. The fixture is not an LLM.

## Verify

```bash
cd experiments/agent-contract-audit-002
export PYTHONPATH="../agent-contract-audit-001:."
python -m unittest discover -s tests -v
python -m aca002 verify-a001
python -m aca002 verify-evidence
python scripts/randomized_protocol_probe.py
python scripts/release_check.py
```

## Live OpenAI Agents SDK lane

The optional live lane is deliberately absent from CI. It requires a real model
name and provider key:

```bash
export OPENAI_API_KEY=...
python -m pip install 'openai-agents>=0.17.6,<0.18'
python -m aca002 live-openai \
  --model "$ACA002_MODEL" \
  --pairs 64 \
  --baseline-runs 8 \
  --output live-out
```

A scientific promotion requires the blind proposer to cover both sides of the
separation and the frozen grader to produce at least one `SUPPORTED` dependency
and one `REJECTED_RITUAL`, with independent replay at zero mismatches.

No live result is checked into this release.
