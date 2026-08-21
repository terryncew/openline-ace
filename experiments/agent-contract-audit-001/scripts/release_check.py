from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
sys.path.insert(0, str(ROOT))

from aca001.evidence import build_evidence, verify_evidence


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_release_manifest() -> dict:
    manifest_path = ROOT / "RELEASE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = manifest["files"]

    actual = {}
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel_local = path.relative_to(ROOT).as_posix()
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if rel_local == "RELEASE_MANIFEST.json":
            continue
        rel_repo = path.relative_to(REPO_ROOT).as_posix()
        actual[rel_repo] = {
            "sha256": digest(path),
            "size": path.stat().st_size,
        }

    workflow = REPO_ROOT / ".github" / "workflows" / "agent-contract-audit-001.yml"
    actual[workflow.relative_to(REPO_ROOT).as_posix()] = {
        "sha256": digest(workflow),
        "size": workflow.stat().st_size,
    }

    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise RuntimeError(f"release closure mismatch missing={missing} extra={extra}")
    for name, metadata in expected.items():
        if actual[name] != metadata:
            raise RuntimeError(f"release file mismatch: {name}")
    return {
        "files": len(expected),
        "base_main": manifest["base_main"],
        "authority": manifest["authority"],
    }


def run() -> None:
    checked = verify_evidence(ROOT / "evidence")
    closure = verify_release_manifest()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "evidence"
        result = build_evidence(out)
        rebuilt = verify_evidence(out)
        if result["verdict"] != "CONFORMANCE_PASS_EXTERNAL_UNRUN":
            raise RuntimeError(result["verdict"])
        if rebuilt["status"] != "VERIFIED":
            raise RuntimeError(rebuilt)
    if checked["status"] != "VERIFIED":
        raise RuntimeError(checked)
    print(json.dumps({
        "status": "PASS",
        "verdict": "CONFORMANCE_PASS_EXTERNAL_UNRUN",
        "scientific_standing": "MECHANICS_ONLY_NOT_EXTERNAL_AGENT_EVIDENCE",
        "external_lane": "UNRUN",
        "release_files": closure["files"],
        "base_main": closure["base_main"],
        "authority": closure["authority"],
    }, sort_keys=True))


if __name__ == "__main__":
    run()
