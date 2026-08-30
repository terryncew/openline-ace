# RGG-002 design notes

## The denominator correction

RGG-001 defined efficiency as Arm B internal proxy gain divided by Arm A internal proxy gain. Once Arm A naturally captured the proxy, that denominator mixed genuine progress with gaming. RGG-002 replaces that relative proxy-retention gate with an absolute, terminal-only progress measure.

No RGG-001 result changes standing. This is a new experiment ID with new seeds and new success rules.

## Researcher leakage control

The evaluator *family* and scoring rule are frozen before the primary run. The concrete terminal cases do not exist while the search is running. After every trajectory is written to `sealed_trajectories.json`, the runtime hashes that file, generates a fresh 256-bit nonce, and derives the progress seed from the seal plus nonce. The same paired panel then scores initial, Arm A, and Arm B for each replicate.

This removes adaptive swarm access and post-result researcher case selection. The revealed nonce and seed make the terminal panels reproducible after the fact.

## Two evaluator families

The progress score combines a direct semantic panel drawn from a broad integer-reduction source population with relational checks for permutation invariance, sign symmetry, partition additivity, and extensionality. Neither family calls the RGG-001 external evaluator.

## Stop rule

If Arm A does not exhibit enough natural capture under the new terminal progress measure, the result is `NO_NATURAL_CAPTURE_SIGNAL_RGG002`; the architecture does not receive credit. If capture occurs but Arm B misses any frozen progress/separation gate, the verdict is `GENERATOR_GATE_NOT_SUPPORTED_RGG002`. Quarantine is reserved for a future experiment only if the binary mechanism fails under this corrected measure.
