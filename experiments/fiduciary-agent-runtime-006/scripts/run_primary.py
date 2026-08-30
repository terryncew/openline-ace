from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from far006.experiment import run_primary


parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True)
args = parser.parse_args()
preregistration = json.loads((ROOT / "PREREGISTRATION.json").read_text())
result = run_primary(pathlib.Path(args.output), preregistration, ROOT)
print(result["verdict"])
