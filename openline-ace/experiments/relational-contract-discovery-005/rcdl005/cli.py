"""Command line interface for RCDL-005."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .domain import verify_domain
from .evidence import freeze_evidence, verify_evidence
from .experiment import run_experiment
from .policies import policy_boundary
from .tournament import verify_exhaustive_oracle
from .verification import verify_manifest, verify_projection


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rcdl005")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--force", action="store_true")
    manifest = commands.add_parser("verify-manifest")
    manifest.add_argument("manifest", type=Path)
    projection = commands.add_parser("verify-projection")
    projection.add_argument("projection", type=Path)
    commands.add_parser("verify-domain")
    commands.add_parser("verify-policy-boundary")
    commands.add_parser("verify-oracle")
    freeze = commands.add_parser("freeze-evidence")
    freeze.add_argument("root", type=Path, nargs="?")
    verify = commands.add_parser("verify-evidence")
    verify.add_argument("root", type=Path, nargs="?")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "run":
            result = run_experiment(args.output, force=args.force)
        elif args.command == "verify-manifest":
            result = verify_manifest(args.manifest).to_dict()
        elif args.command == "verify-projection":
            result = verify_projection(args.projection).to_dict()
        elif args.command == "verify-domain":
            result = verify_domain()
        elif args.command == "verify-policy-boundary":
            result = policy_boundary()
        elif args.command == "verify-oracle":
            result = verify_exhaustive_oracle()
        elif args.command == "freeze-evidence":
            result = freeze_evidence(args.root) if args.root else freeze_evidence()
        elif args.command == "verify-evidence":
            result = verify_evidence(args.root) if args.root else verify_evidence()
        else:  # pragma: no cover
            raise RuntimeError("unreachable command")
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0

