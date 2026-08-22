# OpenLine Continuity Replay 001

This is the first held-out real-history test of the Continuity Observer.

The question is practical: when repository state changes, can receiver-owned dependency tracking reopen only the standing that actually depended on the changed state?

The observer is compared with two baselines: global invalidation, which reopens every claim after a relevant change, and flat latest-state, which reopens only direct claims and ignores descendants.

## Test-leakage control

The replay engine is frozen before the held-out answer key is written. It has no learned parameters or tuned thresholds. Unit tests use only a synthetic development fixture. The held-out corpus contains two external repositories. The held-out oracle is a separate file and is never imported by the engine. CI verifies the exact engine hash before held-out scoring, and any post-freeze engine modification aborts evaluation.

## Held-out histories

1. `microsoft/agent-governance-toolkit` PR #2946, base `2ef3fc2…`, head `2ffe707…`.
2. `vercel-labs/portless` PR #375, base `15ef064…`, head `bd83716…`.

The recorded Git blob identities bind the replay fixture to those immutable states.

## Winning condition

The Continuity Observer must miss zero warranted reopenings, create zero unnecessary reopenings, review fewer claims than global invalidation, and miss fewer descendants than flat latest-state.

This test measures selective reopening given frozen dependency declarations. It does not test automatic dependency discovery.

`policy_authority: NONE`

`runtime_permission: NONE`
