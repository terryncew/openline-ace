from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evidence import build_evidence, verify_evidence
from .tournament import run_tournament


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--output", required=True)
    sub.add_parser("verify-evidence")
    args = parser.parse_args()
    if args.command == "run":
        result = build_evidence(Path(args.output))
        print(json.dumps({"verdict": result["verdict"], "manifest": result["manifest"]}, sort_keys=True))
    elif args.command == "verify-evidence":
        verify_evidence(Path(__file__).resolve().parent.parent / "evidence")
        print("RCDL-007 frozen evidence verified")


if __name__ == "__main__":
    main()
