# Contract Manifest Shape

A supported live candidate may later be projected into a portable contract
manifest. A-001 does not grant runtime authority.

Minimum fields:

- candidate ID and exact clause text;
- scope and workflow identity;
- proposer identity/version with `authority: NONE`;
- exact active, sham, and restoration intervention descriptions;
- original verifier identity;
- task/run boundary;
- paired outcome counts;
- frozen statistical policy;
- active-minus-sham effect interval;
- restoration effect interval;
- nuisance/sham diagnostics;
- evidence artifact hashes;
- standing;
- limitations and reopening conditions;
- `policy_authority: NONE`;
- `compiler_eligible: false` unless a separate receiver policy promotes it.

A later Receipt Gate or monitor compiler must independently verify the manifest
and apply receiver-owned policy. A-001 never emits execution permission.
