from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle_sha(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.as_posix()):
        rel = path.relative_to(ROOT).as_posix().encode("utf-8")
        digest.update(len(rel).to_bytes(4, "big"))
        digest.update(rel)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def main() -> int:
    config = json.loads((ROOT / "experiment_config.json").read_text(encoding="utf-8"))

    engine_files = list((ROOT / "ccr").glob("*.py"))
    actual_engine = bundle_sha(engine_files)
    if actual_engine != config["engine_bundle_sha256"]:
        raise SystemExit(
            f"engine bundle mismatch expected={config['engine_bundle_sha256']} actual={actual_engine}"
        )

    checks = {
        "source_ledger_sha256": ROOT / "sources" / "source_ledger.json",
        "cohort_sha256": ROOT / "sources" / "verra_cquest_completed_qcr.json",
        "case_sha256": ROOT / "fixtures" / "vcs_2372_boeing_case.json",
        "oracle_sha256": ROOT / "oracle" / "vcs_2372_oracle.json",
    }
    for key, path in checks.items():
        actual = sha256(path)
        if actual != config[key]:
            raise SystemExit(f"{key} mismatch expected={config[key]} actual={actual}")

    print("ccr001_frozen_inputs_verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
