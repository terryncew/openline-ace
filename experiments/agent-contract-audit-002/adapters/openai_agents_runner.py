#!/usr/bin/env python3
"""One-request stdin/stdout adapter for A-002 live OpenAI Agents SDK runs."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aca002.live import run_openai_request


def main() -> int:
    request = json.loads(sys.stdin.read())
    tasks = json.loads((ROOT / "fixtures" / "tasks.json").read_text())["tasks"]
    task = next(t for t in tasks if t["task_id"] == request["task_id"])
    model = os.environ.get("ACA002_MODEL")
    if not model:
        raise RuntimeError("ACA002_MODEL must name the live model")
    result = run_openai_request(request, task, model)
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
