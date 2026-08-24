# Standing-Loss Lead-Time 002 (SLD-002)

**Status before external run:** `EXTERNAL_RUN_READY_UNRUN`  
**Policy authority:** `NONE`  
**Runtime permission:** `NONE`

SLD-001 showed the mechanism in a frozen deterministic harness. SLD-002 asks whether the same timing distinction survives real public histories that OpenLine did not design.

## Question

Can exact-state review standing resolve `LOST` before terminal human disposition in real pull-request histories, without collapsing into either "alert on every change" or a fixed evidence TTL?

This is not a prediction test. A post-approval commit first **reopens** standing. It earns no lead-time credit. Standing is counted as lost only when a later decisive re-review on a post-approval commit completes as `CHANGES_REQUESTED`.

```text
APPROVED on commit A
        |
        v
commit B arrives              <- REOPEN only
        |
        v
re-review on post-A commit
        |
        +-- APPROVED ----------> VALID
        |
        +-- CHANGES_REQUESTED -> LOST at t_loss
                                  |
                                  v
                         later PR close/unmerged
                              at t_headline
```

Primary lead time:

`lead_hours = t_headline - t_loss`

## Frozen external population

Two public repositories:

- `astral-sh/ruff`
- `pydantic/pydantic`

Historical window: calendar year 2025.

For each repository the runner takes, in created-ascending order:

- up to 6 closed-unmerged PRs with an approved review;
- up to 6 merged PRs with an approved review.

No repository substitution, window expansion, outcome-dependent replacement, or threshold adjustment is permitted after the first external response.

## Eligibility

A candidate becomes an external replay case only if:

1. GitHub exposes an `APPROVED` review tied to a commit in the PR commit list;
2. at least one later commit lands after that approval and before PR closure;
3. the commit/review history is not truncated at the frozen 100-item cap.

The baseline approval is the earliest approval satisfying those conditions. The reopen time is the first later commit. The first decisive post-change review (`APPROVED` or `CHANGES_REQUESTED`) resolves standing. If no such review occurs before closure, OLP records no resolved standing signal for that case.

## Baselines

- **Headline-only:** learns terminal disposition at `closed_at`; lead = 0.
- **Naive Diff:** treats the first post-approval commit as invalidation. It is earlier by construction, so it is judged on unnecessary invalidation of epochs that later reverify `VALID`.
- **TTL:** invalidates at approval + 24 hours, regardless of whether the bound state changed.

## Verdict

A positive external candidate requires all preregistered conditions:

- enough terminal and valid-control cases from both repositories;
- at least 50% of eligible terminal cases receive a pre-closure `LOST` signal;
- at least 3 terminal cases are detected;
- median detected lead >= 6 hours;
- at least 75% of detected terminal leads are positive;
- OLP unnecessary invalidation on `VALID` re-verification controls is <= 25% of Naive Diff's rate;
- TTL does not Pareto-dominate OLP on coverage, lead, and control churn.

Otherwise the result is `NO_EXTERNAL_STANDING_LOSS_ADVANTAGE`, unless the frozen corpus is too small (`DATA_INSUFFICIENT`) or the public source cannot be read (`SOURCE_ACCESS_FAILED`).

## Freeze

The freeze binds the preregistration, source manifest, evaluator, and external runner before any external fetch. Outcome files are produced only after those hashes verify.

## Run

```bash
python -m unittest discover -s tests -v
python scripts/verify_freeze.py
python scripts/verify_release.py
python scripts/run_external.py
python scripts/verify_result.py
```

The external run writes `external_raw.json`, `external_cases.jsonl`, and `external_result.json`. They are runtime evidence artifacts, not preregistration inputs.
