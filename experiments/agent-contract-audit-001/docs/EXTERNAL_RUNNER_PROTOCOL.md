# External Runner Protocol

A-001 keeps workflow execution outside ACE.

The runner is an adapter owned by the evaluated workflow. It reads exactly one
JSON request from stdin and returns exactly one JSON result on stdout.

Request protocol:

`openline.agent-contract-audit.runner-request.v1`

Required request fields include candidate ID, arm, pair ID, task ID, seed, and
the declarative intervention.

Result protocol:

`openline.agent-contract-audit.runner-result.v1`

Example:

```json
{
  "protocol": "openline.agent-contract-audit.runner-result.v1",
  "candidate_id": "fresh-test-binding",
  "pair_id": "fresh-test-binding:task-7:0003",
  "task_id": "task-7",
  "seed": 10003,
  "arm": "active",
  "runner_status": "ok",
  "verifier": {
    "id": "original-task-verifier-v4",
    "success": false
  },
  "trace_sha256": "..."
}
```

`runner_status` is diagnostic only. It may report that a wrapper blocked,
rewrote, timed out, or otherwise changed execution. The A-001 grader does not
use it as success.

Only `verifier.success` counts for behavioral standing.

The adapter should use common random numbers or otherwise paired seeds when the
underlying provider permits it, but A-001 does not pretend a seed fully controls
a remote model.

No API keys, raw hidden-test data, or model chain-of-thought belong in the
portable result.
