# A-001 Audit Dashboard

| Check | Frozen value |
| --- | --- |
| Experiment | OpenLine Agent Contract Audit 001 |
| Current verdict | `CONFORMANCE_PASS_EXTERNAL_UNRUN` |
| Scientific standing | `MECHANICS_ONLY_NOT_EXTERNAL_AGENT_EVIDENCE` |
| Policy authority | `NONE` |
| Observational runs | 192 |
| Successful observational runs | 181 |
| True dependency prevalence among observational success | 1.000 |
| Ritual prevalence among observational success | 1.000 |
| Conformance candidates | 4 |
| Pairs per candidate | 96 |
| Arms per pair | 4 |
| Load-bearing fixture | `SUPPORTED` |
| Load-bearing active−sham failure Δ | 0.9479 |
| Load-bearing 95% bootstrap interval | [0.8958, 0.9896] |
| Load-bearing restoration Δ | 0.9479 |
| Planted ritual | `REJECTED_RITUAL` |
| Ritual active−sham failure Δ | 0.0000 |
| Sham-sensitive confound | `UNDECIDABLE_SHAM_EFFECT` |
| Confound sham failure rate | 0.7500 |
| Wrapper-manufactured rule | `REJECTED_RITUAL` |
| Supported contract manifests emitted | 1 |
| Manifest compiler eligibility | `false` |
| Blind external agent lane | `UNRUN` |
| Minimum live pairs/candidate | 64 |
| Support effect floor | 0.20 |
| Ritual equivalence band | ±0.08 |
| Sham failure ceiling | 0.20 |

The conformance fixture deliberately makes the planted load-bearing dependency
and the planted ritual observationally indistinguishable: both are present in
100% of successful observational traces. Intervention, not correlation, creates
the separation.

The checked manifest is evidence-only. It carries `policy_authority: NONE` and
`compiler_eligible: false`; a downstream receiver must independently decide
whether any future live contract is admissible for enforcement.
