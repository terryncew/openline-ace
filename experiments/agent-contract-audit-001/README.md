# OpenLine Agent Contract Audit 001

A-001 is the first outward-facing **contract microscope** experiment.

It does not ask whether symbolic RCDL beats a learned baseline. It asks whether
an audit instrument can distinguish a load-bearing workflow dependency from a
highly correlated ritual under stochastic execution.

The architecture is:

```text
trace
  -> untrusted candidate proposer
  -> baseline / active / matched sham / restoration
  -> original external verifier
  -> paired effect estimate
  -> auditable standing
```

The checked first result is intentionally limited to seeded stochastic
conformance mechanics.

Frozen conformance verdict:

`CONFORMANCE_PASS_EXTERNAL_UNRUN`

Scientific standing:

`MECHANICS_ONLY_NOT_EXTERNAL_AGENT_EVIDENCE`

The fixture retains one planted load-bearing artifact-binding dependency,
rejects a scratchpad ritual that is perfectly correlated with observational
success, abstains when the matched sham itself is damaging, and rejects a
wrapper-manufactured rule when the original verifier still succeeds.

The blind external LLM-agent lane is **UNRUN**. It is the empirical proving
ground, not something the fixture may simulate into existence.

Checked conformance numbers:

- 181/192 observational runs succeed;
- both the planted dependency and planted ritual occur in 100% of those successful traces;
- load-bearing active-minus-sham failure delta: 0.9479, 95% paired-bootstrap interval [0.8958, 0.9896];
- ritual active-minus-sham failure delta: 0.0000;
- sham-sensitive confound sham failure rate: 0.7500;
- exactly 1 fixture contract manifest is emitted, with `policy_authority: NONE` and `compiler_eligible: false`.

## Run

```bash
cd experiments/agent-contract-audit-001
export PYTHONPATH="."
python -m unittest discover -s tests -v
python -m aca001 verify-evidence
python -m aca001 conformance --output conformance-out
python scripts/randomized_hostile_probe.py
python scripts/release_check.py
```

Build a proposer packet from an OTel-like trace:

```bash
python -m aca001 proposer-packet --trace trace.json --output proposer-packet.json
```

Run a real external workflow adapter:

```bash
python -m aca001 run-external \
  --candidates candidates.json \
  --tasks tasks.json \
  --runner "python /path/to/adapter.py" \
  --pairs 64 \
  --output external-results.jsonl
```

The adapter contract is in `docs/EXTERNAL_RUNNER_PROTOCOL.md`.

## Boundary

A-001 proposes no production policy and grants no execution authority.
Surviving live contracts would be evidence for downstream receiver-owned
systems such as Claim Graph and Receipt Gate, not self-executing rules.
