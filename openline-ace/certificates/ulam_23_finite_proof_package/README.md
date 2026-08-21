# U(2,3) Finite Proof Package

This is the finite proof/certificate package for the U(2,3) 400k ACE promotion run.

It verifies a finite computational claim. It does not prove the infinite hidden-clock conjecture.

Main entry:
- `ULAM_23_FINITE_PROOF_PACKAGE.md`

Verifier:
- `verify_finite_certificate_u23_400k.py`

Certificate:
- `finite_certificate_u23_400k.json`

Data:
- `data/ulam_2_3_values_400000.bin`
- `data/ulam_2_3_counts_saturated_400000.bin`

Run:

```bash
python3 verify_finite_certificate_u23_400k.py --skip-prefix-rule-check
```

Run the full slower prefix-rule check:

```bash
python3 verify_finite_certificate_u23_400k.py
```


## Verification status

Fast finite metric verification: `finite_certificate_verified`.

Full greedy prefix verification has completed:

```text
verdict: full_greedy_prefix_verified
counts_mismatches: 0
elapsed_cpu_seconds: 21.27
```

Run it again with:

```bash
./verify_ulam23_prefix_full data/ulam_2_3_values_400000.bin data/ulam_2_3_counts_saturated_400000.bin 400000
```
