from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-v"],cwd=ROOT,check=True)
subprocess.run([sys.executable,"scripts/build_conformance.py"],cwd=ROOT,check=True)
subprocess.run([sys.executable,"scripts/verify_bundle_independent.py","evidence/conformance-bundle"],cwd=ROOT,check=True)
for py in ROOT.rglob("*.py"): compile(py.read_text(encoding="utf-8"),str(py),"exec")
print("aca003_release_check_pass")
