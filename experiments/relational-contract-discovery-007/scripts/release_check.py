from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from rcdl007.evidence import build_evidence, verify_evidence
from rcdl007.tournament import run_tournament


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identities", type=int, default=16)
    args = parser.parse_args()
    result = run_tournament(args.identities)
    if result["verdict"] != "PRE_ADJUDICATION_CAUSAL_PARITY":
        raise RuntimeError(result["verdict"])
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp)
        build_evidence(output, args.identities)
        verify_evidence(output)
    print(
        {
            "verdict": result["verdict"],
            "rows": len(result["rows"]),
            "symbolic": result["metrics"]["symbolic"],
            "learned": result["metrics"]["learned"],
            "transport_failures": result["transport_failures"],
        }
    )


if __name__ == "__main__":
    main()
