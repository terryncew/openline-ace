from __future__ import annotations
import json, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "README.md", "CLAIM_BOUNDARY.md", "SOURCE_CONTEXT.json", "PREREGISTRATION_TEMPLATE.json",
    "dma001/__init__.py", "dma001/__main__.py", "dma001/grader.py",
    "fixtures/conformance-results.jsonl", "tests/test_dma001.py",
    "scripts/verify_conformance_independent.py", "docs/PROTOCOL.md", "docs/NOTEBOOKLM_SOURCE.md"
]
missing = [p for p in required if not (ROOT / p).is_file()]
if missing:
    raise SystemExit(f"missing required files: {missing}")
manifest = {}
for p in required:
    b = (ROOT/p).read_bytes()
    manifest[p] = {"sha256": hashlib.sha256(b).hexdigest(), "size": len(b)}
print(json.dumps({"release_closure": True, "file_count": len(manifest), "files": manifest, "authority":"NONE"}, sort_keys=True))
