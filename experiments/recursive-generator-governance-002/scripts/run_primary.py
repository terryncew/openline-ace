from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rgg002.experiment import run_primary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = run_primary(output=args.output)
    print(json.dumps({
        "experiment_id": result["experiment_id"],
        "scientific_standing": result["scientific_standing"],
        "verdict": result["verdict"],
        "metrics": result["metrics"],
        "integrity": result["integrity"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
