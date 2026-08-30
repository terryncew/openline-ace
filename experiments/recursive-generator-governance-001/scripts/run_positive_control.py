from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rgg001.evaluator import positive_control


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = positive_control()
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "positive_control.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit("positive control failed: primary null would be uninterpretable")


if __name__ == "__main__":
    main()
