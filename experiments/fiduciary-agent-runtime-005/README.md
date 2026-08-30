# FAR-005 — Dependency-Linked Repository Pressure Test

FAR-005 graduates the Assurance Runtime from the three-function reference substrate to a multi-file dependency DAG:

```
codec.py -> parse.py -> pipeline.py
transform.py ---------> pipeline.py
```

The runtime must do five things at once: permit genuine ordered unblocking, expand consequence checks to frozen downstream consumers, reject a transform patch that looks locally successful but breaks the pipeline contract, keep authority/evaluator surfaces outside agent control, and preserve causal receipt inheritance strongly enough to selectively REOPEN descendants when codec evidence is revoked.

The Generator Gate / Receipt Gate authority membrane is imported from the frozen FAR-003 implementation and SHA-256 pinned. FAR-005 adds a dependency-aware scope/consequence layer and a minimal claim-standing graph; it does not replace the validated membrane.

The primary run is manual only. Mechanics, freeze verification, upstream pins, and non-evidentiary power controls run on PR/push. `HALT_SATURATED` remains disabled so post-convergence churn is observable.
