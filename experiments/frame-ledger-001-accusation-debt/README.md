# Frame Ledger 001 — Accusation Debt / Revocation Leakage

Status: **UNRUN EXPERIMENT PACKAGE**

This experiment asks one narrow question:

> When the factual record is held fixed, can a refuted or explicitly withdrawn accusation continue to affect a receiver's judgment or action, and can defensive tone create additional penalty without adding evidence?

It does not assume that a distinct mechanism called a frame exists.

## Arms

Each fictional case uses the same underlying evidence.

- `control` — evidence only.
- `matched_nuisance` — same evidence plus a similarly structured but explicitly irrelevant administrative notice.
- `accusation_refuted` — accusation first, then evidence, then independent refutation.
- `accusation_refuted_evidence_first` — same ingredients, but evidence appears before accusation/refutation.
- `explicit_revocation` — accusation is explicitly labeled `STANDING: WITHDRAWN`; evidence and refutation are labeled `ACTIVE`.
- `calm_defense` — refuted accusation plus a calm denial with no new factual content.
- `angry_defense` — same factual denial with anger added.

## Primary contrasts

The scorer reports separate quantities rather than a universal score:

- accusation debt versus evidence-only control;
- accusation-specific effect versus matched nuisance;
- order sensitivity;
- explicit revocation leakage;
- calm-versus-angry defense penalty;
- action escalation;
- evidence contamination when non-evidentiary inputs are cited as basis;
- cross-receiver heterogeneity of those effects.

The scorer fails closed on missing arms, duplicate result keys, and unequal replicate sets.

## Interpretation

**KILL** if the effects disappear under the controls or receiver identity adds no useful information beyond ordinary model-level performance.

**PIVOT** if a robust effect is adequately described by a narrower known mechanism such as order sensitivity, continued influence, tone bias, or instruction following.

**CANDIDATE** only if an explicitly withdrawn input continues to change standing/action under fixed facts and the effect is reproducible, especially if receivers differ systematically in whether they honor revocation.

## Run shape

Recommended first pass:

- 8 cases
- 7 arms
- at least 3 isolated replicates per arm
- at least 3 materially different receiving models
- tools off, no conversation memory, fixed system prompt and equivalent decoding settings where possible

That is 504 calls at 3 receivers × 8 cases × 7 arms × 3 replicates.

## Quick start

```bash
python src/render.py --out data/prompts.jsonl
python -m unittest discover -s tests -v
python src/score.py data/example_results.jsonl
```

`data/example_results.jsonl` is synthetic and exists only to exercise the scorer. It is not experimental evidence.

## Boundary

This measures operational judgment, not consciousness or subjective frames of reference. It does not claim a general law of accusation and does not resurrect older OpenLine or Coherence Dynamics claims.
