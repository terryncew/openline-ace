#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, zipfile, sys

ROOT = Path(__file__).resolve().parents[1]
AR = ROOT / "assurance-runtime"
ARCHIVE = AR / "evidence" / "far-006"
EXPECTED_ZIP = "781f00a4dc6cb082d626ffd9e6eb58341bc59b7fc7f1b7f211231f672680701b"
EXPECTED_RESULT = "bb6acdaac8c7c0274659a2243016c3f9a9e3736ad939794ac584f76924f33de8"
EXPECTED_MAIN = "c7c39282a332710c848a950709bf84d265e1e6f9"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fail(msg):
    raise SystemExit("FAIL: " + msg)

zpath = ARCHIVE / "FIDUCIARY-AGENT-RUNTIME-006-primary.zip"
if not zpath.exists() or sha(zpath) != EXPECTED_ZIP:
    fail("FAR-006 original artifact ZIP hash mismatch")

rpath = ARCHIVE / "result.json"
if not rpath.exists() or sha(rpath) != EXPECTED_RESULT:
    fail("FAR-006 result.json hash mismatch")

declared = (ARCHIVE / "result.sha256").read_text().strip().split()[0]
if declared != EXPECTED_RESULT:
    fail("result.sha256 does not bind canonical result")

with zipfile.ZipFile(zpath) as z:
    expected_names = {
        "external_source_receipt.json",
        "power_calibration.json",
        "result.json",
        "result.sha256",
    }
    if set(z.namelist()) != expected_names:
        fail("original FAR-006 ZIP member set changed")
    for name in expected_names:
        if z.read(name) != (ARCHIVE / name).read_bytes():
            fail(f"archived {name} differs from original ZIP")

manifest = json.loads((ARCHIVE / "ARCHIVE_MANIFEST.json").read_text())
if manifest["canonical"]["result_json_sha256"] != EXPECTED_RESULT:
    fail("archive manifest result pin mismatch")
if manifest["canonical"]["original_actions_zip_sha256"] != EXPECTED_ZIP:
    fail("archive manifest ZIP pin mismatch")

freeze = json.loads((AR / "FAR_LINE_FREEZE.json").read_text())
if freeze.get("status") != "FROZEN":
    fail("FAR line is not frozen")
if freeze.get("terminal_experiment") != "FIDUCIARY-AGENT-RUNTIME-006":
    fail("unexpected terminal FAR experiment")
if freeze.get("no_successor") != "FAR-007":
    fail("freeze does not explicitly prohibit FAR-007")
if freeze.get("terminal_result_sha256") != EXPECTED_RESULT:
    fail("freeze result pin mismatch")

for forbidden in (
    ROOT / "FAR-007.md",
    ROOT / "experiments" / "fiduciary-agent-runtime-007",
):
    if forbidden.exists():
        fail(f"FAR line is frozen; forbidden successor exists: {forbidden.relative_to(ROOT)}")

spec = (ROOT / "ASSURANCE_RUNTIME.md").read_text()
required = [
    "Generator Gate contract",
    "Mandate & Policy Gate contract",
    "Receipt Gate contract",
    "Claim Graph & Frame Ledger contract",
    "Explicit non-claims",
    "There is **no FAR-007**",
    EXPECTED_RESULT,
    EXPECTED_ZIP,
]
for token in required:
    if token not in spec:
        fail(f"ASSURANCE_RUNTIME.md missing required closeout token: {token}")

print("PASS Assurance Runtime closeout")
print("FAR-006 result SHA-256:", EXPECTED_RESULT)
print("FAR-006 artifact ZIP SHA-256:", EXPECTED_ZIP)
print("FAR line: FROZEN at FAR-006; FAR-007 prohibited")
