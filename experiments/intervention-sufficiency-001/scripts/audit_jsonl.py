from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from is001.core import audit_rows, load_jsonl, load_policy


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit intervention-corpus sufficiency")
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_rows(load_jsonl(args.jsonl), load_policy())
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    if report["verdict"] == "INVALID_INTERVENTION_CORPUS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
