from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from far006.controls import run_controls


result = run_controls(ROOT)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["passed"] else 1)
