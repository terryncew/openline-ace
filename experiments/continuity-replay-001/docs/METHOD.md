# Method

Continuity Replay 001 tests reopening economics and recall, not a similarity score.

For each real historical transition: freeze a baseline claim graph; observe changed repository paths; run three reopening policies; compare predictions with a held-out answer key; count warranted, missed, and excess reviews.

The Continuity Observer uses graph reachability only. There is no training, threshold fitting, semantic embedding, or repository-specific conditional in the engine.

## Why the oracle is separate

The engine receives changed artifact roots and dependency edges. The held-out oracle records which claims should be reopened or retained. Static checks ensure engine modules cannot reference evaluation-only material. The engine bundle hash is frozen before scoring.

This prevents the common failure mode where implementation code is edited against test labels until the benchmark turns green.
