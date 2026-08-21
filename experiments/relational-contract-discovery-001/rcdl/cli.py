"""Command-line interface for RCDL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .calibration import run_calibration
from .canonical import load_json_bytes
from .evaluator import evaluate
from .evidence import freeze_evidence, verify_evidence
from .manifest import verify_manifest
from .miner import filter_candidates
from .model import Clause
from .otel import trace_from_otlp
from .projection import verify_projection
from .raft import raft_candidate_clauses
from .reference import verify_reference
from .trace import Trace


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rcdl")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-clause", help="validate and digest a clause")
    validate.add_argument("clause", type=Path)

    evaluate_parser = subparsers.add_parser("evaluate", help="evaluate a clause over a trace")
    evaluate_parser.add_argument("clause", type=Path)
    evaluate_parser.add_argument("trace", type=Path)

    calibrate = subparsers.add_parser("calibrate", help="run the deterministic Raft calibration")
    calibrate.add_argument("--output", type=Path, required=True)
    calibrate.add_argument("--trials", type=int, default=8)
    calibrate.add_argument("--force", action="store_true")

    verify = subparsers.add_parser("verify-manifest", help="verify canonical bytes and digest binding")
    verify.add_argument("manifest", type=Path)

    verify_projection_parser = subparsers.add_parser(
        "verify-projection", help="verify the fail-closed downstream projection"
    )
    verify_projection_parser.add_argument("projection", type=Path)

    verify_reference_parser = subparsers.add_parser(
        "verify-reference", help="verify the pinned official Raft specification"
    )
    verify_reference_parser.add_argument("record", type=Path, nargs="?")

    ingest = subparsers.add_parser("ingest-otel", help="normalize an OTLP JSON trace")
    ingest.add_argument("input", type=Path)
    ingest.add_argument("output", type=Path)

    mine = subparsers.add_parser(
        "mine-candidates", help="propose clauses supported by declared successful traces"
    )
    mine.add_argument("--clauses", type=Path, required=True)
    mine.add_argument("--traces", type=Path, nargs="+", required=True)
    mine.add_argument("--min-support", type=int, default=2)

    freeze = subparsers.add_parser("freeze-evidence", help="freeze the bounded evidence set")
    freeze.add_argument("root", type=Path, nargs="?")

    verify_evidence_parser = subparsers.add_parser(
        "verify-evidence", help="verify frozen evidence and source binding"
    )
    verify_evidence_parser.add_argument("root", type=Path, nargs="?")

    subparsers.add_parser("show-candidates", help="print the frozen Raft candidates")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate-clause":
            clause = Clause.from_path(args.clause)
            result = {"valid": True, "id": clause.id, "digest": clause.digest}
        elif args.command == "evaluate":
            result = evaluate(Clause.from_path(args.clause), Trace.from_path(args.trace)).to_dict()
        elif args.command == "calibrate":
            result = run_calibration(args.output, trials=args.trials, force=args.force)
        elif args.command == "verify-manifest":
            result = verify_manifest(args.manifest).to_dict()
        elif args.command == "verify-projection":
            result = verify_projection(args.projection).to_dict()
        elif args.command == "verify-reference":
            result = (
                verify_reference(args.record).to_dict()
                if args.record
                else verify_reference().to_dict()
            )
        elif args.command == "ingest-otel":
            document = load_json_bytes(args.input.read_bytes())
            if not isinstance(document, dict):
                raise ValueError("OTLP input must be an object")
            trace = trace_from_otlp(document)
            trace.write(args.output)
            result = {
                "normalized": True,
                "run_id": trace.run_id,
                "event_count": len(trace.events),
                "output": str(args.output),
            }
        elif args.command == "mine-candidates":
            clause_paths = sorted(args.clauses.glob("*.json"))
            candidates = tuple(Clause.from_path(path) for path in clause_paths)
            traces = tuple(Trace.from_path(path) for path in args.traces)
            proposals = filter_candidates(
                candidates,
                traces,
                min_support=args.min_support,
            )
            result = {
                "schema": "rcdl.candidate-proposals/0.1",
                "candidate_count": len(proposals),
                "accepted_count": sum(item.accepted for item in proposals),
                "oracle_labels_used": False,
                "results": [item.to_dict() for item in proposals],
            }
        elif args.command == "freeze-evidence":
            result = freeze_evidence(args.root) if args.root else freeze_evidence()
        elif args.command == "verify-evidence":
            result = verify_evidence(args.root) if args.root else verify_evidence()
        elif args.command == "show-candidates":
            result = {
                "schema": "rcdl.candidate-list/0.1",
                "clauses": [clause.to_dict() for clause in raft_candidate_clauses()],
            }
        else:  # pragma: no cover
            raise RuntimeError("unreachable command")
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    if args.command == "calibrate" and result["verdict"] != "CALIBRATION_PASS":
        return 1
    return 0
