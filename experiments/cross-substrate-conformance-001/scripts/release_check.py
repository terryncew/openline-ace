import ast, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def run(cmd): subprocess.run(cmd, cwd=ROOT, check=True)
run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
run([sys.executable, "-m", "ace_xs", "--out", "evidence/result.json"])
run([sys.executable, "scripts/verify_evidence.py"])
files = list(ROOT.rglob("*.py"))
for version in ((3,11),(3,12),(3,13)):
    for path in files:
        ast.parse(path.read_text(), filename=str(path), feature_version=version)
print(f"cross_substrate_release_check_pass python_files={len(files)}")
