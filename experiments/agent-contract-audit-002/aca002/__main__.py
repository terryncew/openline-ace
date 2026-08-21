from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evidence import build_conformance, verify_evidence
from .pin import verify_a001_pin


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    p = argparse.ArgumentParser(prog="python -m aca002")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify-a001")
    c = sub.add_parser("conformance")
    c.add_argument("--output", default="conformance-out")
    v = sub.add_parser("verify-evidence")
    v.add_argument("--evidence", default="evidence")
    live = sub.add_parser("live-openai")
    live.add_argument("--model", required=True)
    live.add_argument("--pairs", type=int, default=64)
    live.add_argument("--baseline-runs", type=int, default=8)
    live.add_argument("--output", default="live-out")
    args = p.parse_args()
    if args.cmd == "verify-a001":
        print(json.dumps(verify_a001_pin(), sort_keys=True))
    elif args.cmd == "conformance":
        print(json.dumps(build_conformance(root(), Path(args.output)), sort_keys=True))
    elif args.cmd == "verify-evidence":
        print(json.dumps(verify_evidence(root() / args.evidence), sort_keys=True))
    elif args.cmd == "live-openai":
        from .live_pipeline import run_live
        print(json.dumps(run_live(root(), Path(args.output), model_name=args.model, pairs=args.pairs, baseline_runs=args.baseline_runs), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
