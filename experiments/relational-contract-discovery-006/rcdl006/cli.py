"""Command line interface for RCDL-006."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .fixtures import load_fixtures
from .model import Split
from .policies import policy_boundary
from .tournament import run_tournament
from .upstream import verify_upstream
from .verification import verify_manifest, verify_projection


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rcdl006")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--force", action="store_true")
    manifest = commands.add_parser("verify-manifest")
    manifest.add_argument("manifest", type=Path)
    projection = commands.add_parser("verify-projection")
    projection.add_argument("projection", type=Path)
    commands.add_parser("verify-upstream")
    commands.add_parser("verify-fixtures")
    commands.add_parser("verify-policy-boundary")
    freeze = commands.add_parser("freeze-evidence")
    freeze.add_argument("root", type=Path, nargs="?")
    verify = commands.add_parser("verify-evidence")
    verify.add_argument("root", type=Path, nargs="?")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "run":
            result = run_tournament(args.output, force=args.force)
        elif args.command == "verify-manifest":
            result = verify_manifest(args.manifest).to_dict()
        elif args.command == "verify-projection":
            result = verify_projection(args.projection).to_dict()
        elif args.command == "verify-upstream":
            result = verify_upstream()
        elif args.command == "verify-fixtures":
            fixtures = load_fixtures()
            result = {
                "development_proposals": len(fixtures.by_split(Split.DEVELOPMENT)),
                "evaluation_proposals": len(fixtures.by_split(Split.EVALUATION)),
                "valid": True,
            }
        elif args.command == "verify-policy-boundary":
            result = policy_boundary()
        elif args.command in {"freeze-evidence", "verify-evidence"}:
            from .evidence import freeze_evidence, verify_evidence

            if args.command == "freeze-evidence":
                result = freeze_evidence(args.root) if args.root else freeze_evidence()
            else:
                result = verify_evidence(args.root) if args.root else verify_evidence()
        else:  # pragma: no cover
            raise RuntimeError("unreachable command")
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc), "ok": False}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0
