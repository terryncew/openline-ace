from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rgg001.experiment import run_primary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--meta-seed")
    parser.add_argument("--external-seed")
    args = parser.parse_args()
    result = run_primary(
        root=ROOT,
        output=args.output,
        meta_seed=args.meta_seed,
        external_seed=args.external_seed,
    )
    print(json.dumps({
        "experiment_id": result["experiment_id"],
        "scientific_standing": result["scientific_standing"],
        "verdict": result["verdict"],
        "metrics": result["metrics"],
        "integrity": result["integrity"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
