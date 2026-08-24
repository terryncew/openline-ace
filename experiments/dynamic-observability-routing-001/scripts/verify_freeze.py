from pathlib import Path
from hashlib import sha256
import json

ROOT = Path(__file__).resolve().parents[1]
freeze = json.loads((ROOT / "FREEZE.json").read_text())
errors = []
for entry in freeze["files"]:
    path = ROOT / entry["path"]
    if not path.is_file():
        errors.append(f"missing:{entry['path']}")
        continue
    data = path.read_bytes()
    if len(data) != entry["bytes"]:
        errors.append(f"bytes:{entry['path']}")
    if sha256(data).hexdigest() != entry["sha256"]:
        errors.append(f"sha256:{entry['path']}")
if freeze.get("verdict") != "NO_ROUTING_ADVANTAGE":
    errors.append("verdict")
if freeze.get("runtime_permission") != "NONE":
    errors.append("runtime_permission")
if freeze.get("policy_authority") != "NONE":
    errors.append("policy_authority")
print(json.dumps({"valid": not errors, "errors": errors, "files": len(freeze["files"])}, indent=2, sort_keys=True))
raise SystemExit(0 if not errors else 2)
