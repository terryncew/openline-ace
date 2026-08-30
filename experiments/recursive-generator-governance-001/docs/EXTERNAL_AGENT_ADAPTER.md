# External agent extension

RGG-001's reference generator emits compact algorithm configurations so the
constitutional mechanism can be tested without depending on a commercial LLM.
A later external replication may replace that generator with coding agents or
a swarm, but it must preserve the same seams:

- the agent receives `E_task` feedback for operational work;
- generator-level changes are classified outside the agent;
- Arm B receives only the Generator Gate decision and receipt;
- `E_meta` has an explicit query budget and rotation rule;
- the terminal `E_external` suite is never queried during search;
- all generator-affecting shared infrastructure defaults to Tier 2;
- changes to `E_meta` remain principal-owned Tier 3.

An external replication requires a new experiment ID and fresh preregistration.
Its results may not be pooled with this reference substrate after the fact.
