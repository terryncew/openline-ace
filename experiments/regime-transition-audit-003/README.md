# Regime Transition Audit 003 (RTA-003)

**Status before run:** `EXTERNAL_RUN_READY_UNRUN`  
**Policy authority:** `NONE`

RTA-003 is the final planned test in the current regime-transition line.

RTA-002 returned `DATA_INSUFFICIENT` because only 22 cases survived its frozen Kubernetes-only design. RTA-003 does not repair that run. It starts a new preregistered experiment with a larger source population.

## Question

Does the unchanged RTA-001 transition signal beat freshness alone on a larger, heterogeneous public review-history corpus?

## Frozen external population

Four public repositories:

- `kubernetes/kubernetes`
- `microsoft/vscode`
- `rust-lang/rust`
- `golang/go`

Frozen historical window:

`2025-01-01` through `2025-12-31`

Maximum search intake: 100 merged pull requests per repository.

## What remains unchanged

RTA-001 thresholds:

- dependency churn >= 0.55
- contradiction rate >= 0.30
- support withdrawal rate >= 0.25
- transition event requires 2 of 3 dimensions

The freshness comparator and promotion margins are unchanged.

## Anti-rescue rule

This experiment is terminal for the current line.

After external outcomes are fetched, no:

- source-window expansion;
- repository substitution;
- threshold adjustment;
- feature redefinition;
- sample-floor reduction.

If the result is `NO_PREDICTIVE_ADVANTAGE`, the current regime-transition hypothesis is frozen as unsupported.

If the result is `DATA_INSUFFICIENT`, the current line is also frozen. A future revival would require a materially different data source and a new hypothesis, not RTA-004 with looser inclusion rules.

## Cross-repository guard

A candidate cannot win merely by dominating one repository.

It must clear the frozen aggregate balanced-accuracy and Brier margins and cannot trail freshness by more than 0.02 balanced accuracy in any repository with at least 20 held-out cases.

## Allowed verdicts

- `PREDICTIVE_ADVANTAGE_CANDIDATE`
- `NO_PREDICTIVE_ADVANTAGE`
- `DATA_INSUFFICIENT`

No verdict grants execution or policy authority.
