from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from is002.external import run_external


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-a", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run_external(stage_a_dir=args.stage_a, output_dir=args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["verdict"] == "INVALID_EXTERNAL_INTERVENTION_CORPUS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
