#!/usr/bin/env python3
"""Stdlib-only verifier for A-002 result files; imports no aca002 code."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--tasks", default="fixtures/tasks.json")
    args = ap.parse_args()
    tasks_doc = json.loads(Path(args.tasks).read_text())
    tasks = {t["task_id"]: t for t in tasks_doc["tasks"]}
    errors = []
    rows = 0
    for line_no, line in enumerate(Path(args.results).read_text().splitlines(), 1):
        if not line.strip():
            continue
        rows += 1
        r = json.loads(line)
        task = tasks.get(r.get("task_id"))
        if task is None:
            errors.append([line_no, "unknown_task"])
            continue
        expected = r.get("final_output_sha256") == h(str(task["current_token"]))
        verifier = r.get("verifier", {})
        if verifier.get("id") != tasks_doc["verifier_id"]:
            errors.append([line_no, "verifier_id"])
        if verifier.get("success") is not expected:
            errors.append([line_no, "success_mismatch"])
    print(json.dumps({"rows": rows, "errors": errors, "verified": not errors}, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
