from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "continuity_replay"
FREEZE = json.loads((ROOT / "protocol" / "engine_freeze.json").read_text())
CORPUS = json.loads((ROOT / "heldout" / "corpus.json").read_text())

def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

def main() -> int:
    current = {}
    for path in sorted(PKG.glob("*.py")):
        text = path.read_text(encoding="utf-8").lower()
        for token in ("heldout", "oracle.json"):
            if token in text:
                raise AssertionError(f"engine references evaluation-only material: {path}")
        current[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if current != FREEZE["engine_files"]:
        raise AssertionError("engine changed after freeze")
    bundle = hashlib.sha256(canonical(current)).hexdigest()
    if bundle != FREEZE["engine_bundle_sha256"] or CORPUS["engine_bundle_sha256"] != bundle:
        raise AssertionError("engine freeze binding mismatch")
    oracle_path = ROOT / "heldout" / "oracle.json"
    oracle_hash = hashlib.sha256(canonical(json.loads(oracle_path.read_text()))).hexdigest()
    if oracle_hash != "e4b81ef21109115e7775182a6ae8531cc82283794d336c3bdd79092cad09b8ea":
        raise AssertionError("held-out oracle hash mismatch")
    print("no_test_leakage_verified")
    print("engine_bundle_sha256=" + bundle)
    print("heldout_oracle_sha256=" + oracle_hash)
    return 0
if __name__ == "__main__": raise SystemExit(main())
