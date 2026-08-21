from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit import grade_audit
from .canonical import write_json
from .conformance import build_fixture_results, fixture_candidates, run_conformance
from .evidence import build_evidence, verify_evidence
from .external import build_request, command_from_string, run_external
from .model import ArmResult, AuditPolicy
from .proposer import load_candidates
from .trace import build_proposer_packet


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "evidence"


def _load_results(path: Path) -> list[ArmResult]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(ArmResult.from_mapping(json.loads(line)))
    return rows


def cmd_conformance(args: argparse.Namespace) -> None:
    output = Path(args.output)
    result = run_conformance()
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "summary.json", {
        "verdict": result["verdict"],
        "scientific_standing": result["scientific_standing"],
        "observed_standings": result["observed_standings"],
        "blind_external_lane": result["blind_external_lane"],
    })
    print(json.dumps({
        "verdict": result["verdict"],
        "scientific_standing": result["scientific_standing"],
        "observed_standings": result["observed_standings"],
    }, sort_keys=True))


def cmd_build_evidence(args: argparse.Namespace) -> None:
    result = build_evidence(Path(args.output))
    print(json.dumps({
        "verdict": result["verdict"],
        "scientific_standing": result["scientific_standing"],
    }, sort_keys=True))


def cmd_verify_evidence(args: argparse.Namespace) -> None:
    print(json.dumps(verify_evidence(Path(args.output)), sort_keys=True))


def cmd_proposer_packet(args: argparse.Namespace) -> None:
    packet = build_proposer_packet(Path(args.trace))
    if args.output:
        write_json(Path(args.output), packet)
    print(json.dumps({
        "trace_sha256": packet["trace_sha256"],
        "span_count": packet["span_count"],
        "proposer_authority": packet["proposer_authority"],
    }, sort_keys=True))


def cmd_grade_import(args: argparse.Namespace) -> None:
    candidates = load_candidates(Path(args.candidates))
    results = _load_results(Path(args.results))
    audit = grade_audit(candidates, results, AuditPolicy())
    output = Path(args.output)
    write_json(output, audit)
    print(json.dumps({
        "supported": audit["supported"],
        "rejected_rituals": audit["rejected_rituals"],
        "undecidable": audit["undecidable"],
        "authority": audit["authority"],
    }, sort_keys=True))


def cmd_run_external(args: argparse.Namespace) -> None:
    candidates = load_candidates(Path(args.candidates))
    tasks = json.loads(Path(args.tasks).read_text(encoding="utf-8"))
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks must be a non-empty JSON array")
    command = command_from_string(args.runner)
    rows: list[ArmResult] = []
    for candidate in candidates:
        for pair_index in range(args.pairs):
            task = tasks[pair_index % len(tasks)]
            task_id = str(task["task_id"])
            pair_id = f"{candidate['candidate_id']}:{task_id}:{pair_index:04d}"
            seed = args.seed_offset + pair_index
            for arm in ("baseline", "active", "sham", "restoration"):
                request = build_request(
                    candidate,
                    arm=arm,
                    pair_id=pair_id,
                    task_id=task_id,
                    seed=seed,
                )
                rows.append(run_external(command, request, timeout=args.timeout))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(r.as_dict(), sort_keys=True, separators=(",", ":")) + "\n" for r in rows),
        encoding="utf-8",
    )
    audit = grade_audit(candidates, rows, AuditPolicy())
    write_json(output.with_suffix(".grades.json"), audit)
    print(json.dumps({
        "rows": len(rows),
        "supported": audit["supported"],
        "rejected_rituals": audit["rejected_rituals"],
        "undecidable": audit["undecidable"],
        "authority": "NONE",
    }, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(prog="aca001")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("conformance")
    p.add_argument("--output", default="conformance-out")
    p.set_defaults(func=cmd_conformance)

    p = sub.add_parser("build-evidence")
    p.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    p.set_defaults(func=cmd_build_evidence)

    p = sub.add_parser("verify-evidence")
    p.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    p.set_defaults(func=cmd_verify_evidence)

    p = sub.add_parser("proposer-packet")
    p.add_argument("--trace", required=True)
    p.add_argument("--output")
    p.set_defaults(func=cmd_proposer_packet)

    p = sub.add_parser("grade-import")
    p.add_argument("--candidates", required=True)
    p.add_argument("--results", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_grade_import)

    p = sub.add_parser("run-external")
    p.add_argument("--candidates", required=True)
    p.add_argument("--tasks", required=True)
    p.add_argument("--runner", required=True)
    p.add_argument("--pairs", type=int, default=64)
    p.add_argument("--seed-offset", type=int, default=10000)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_run_external)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
