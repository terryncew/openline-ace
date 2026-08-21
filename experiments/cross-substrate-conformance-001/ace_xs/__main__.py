from pathlib import Path
import argparse
from .run import write_evidence

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="evidence/result.json")
    a = p.parse_args()
    result = write_evidence(Path(a.out))
    print("ACE CROSS-SUBSTRATE CONFORMANCE 001\n")
    for r in result["records"]:
        print(f"{r['substrate_class']:<24} {r['candidate']['candidate_id']:<24} {r['grade']['standing']}")
    print(f"\n{result['supported_count']} load-bearing dependencies kept; {result['ritual_rejected_count']} observational rituals rejected.")
    print("Verdict:", result["status"])
    print("Authority: NONE")
    return 0 if result["status"] == "CROSS_SUBSTRATE_CONFORMANCE_PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
