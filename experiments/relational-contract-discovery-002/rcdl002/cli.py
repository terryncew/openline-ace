"""Command-line interface for the RCDL-002 calibration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .calibration import run_calibration
from .engine_reference import verify_engine_reference
from .evidence import freeze_evidence, verify_evidence
from .manifest import verify_manifest
from .projection import verify_projection
from .workflow import workflow_candidate_clauses


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rcdl002")
    subparsers = parser.add_subparsers(dest="command", required=True)
    calibrate = subparsers.add_parser("calibrate")
    calibrate.add_argument("--output", type=Path, required=True)
    calibrate.add_argument("--trials", type=int, default=8)
    calibrate.add_argument("--force", action="store_true")
    verify_manifest_parser = subparsers.add_parser("verify-manifest")
    verify_manifest_parser.add_argument("manifest", type=Path)
    verify_projection_parser = subparsers.add_parser("verify-projection")
    verify_projection_parser.add_argument("projection", type=Path)
    verify_engine_parser = subparsers.add_parser("verify-engine")
    verify_engine_parser.add_argument("reference", type=Path, nargs="?")
    freeze = subparsers.add_parser("freeze-evidence")
    freeze.add_argument("root", type=Path, nargs="?")
    verify = subparsers.add_parser("verify-evidence")
    verify.add_argument("root", type=Path, nargs="?")
    subparsers.add_parser("show-candidates")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "calibrate":
            result = run_calibration(args.output, trials=args.trials, force=args.force)
        elif args.command == "verify-manifest":
            result = verify_manifest(args.manifest).to_dict()
        elif args.command == "verify-projection":
            result = verify_projection(args.projection).to_dict()
        elif args.command == "verify-engine":
            result = (
                verify_engine_reference(args.reference).to_dict()
                if args.reference
                else verify_engine_reference().to_dict()
            )
        elif args.command == "freeze-evidence":
            result = freeze_evidence(args.root) if args.root else freeze_evidence()
        elif args.command == "verify-evidence":
            result = verify_evidence(args.root) if args.root else verify_evidence()
        elif args.command == "show-candidates":
            result = {
                "schema": "rcdl.candidate-list/0.2",
                "clauses": [clause.to_dict() for clause in workflow_candidate_clauses()],
            }
        else:
            raise RuntimeError("unreachable command")
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    if args.command == "calibrate" and result["verdict"] != "CALIBRATION_PASS":
        return 1
    return 0
