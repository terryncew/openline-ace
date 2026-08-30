from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from far006.external_task import load_task, verify_local_artifacts


result = verify_local_artifacts(ROOT, load_task(ROOT))
assert result["passed"], result
print(f"PASS external task artifacts={len(result['artifacts'])}")
