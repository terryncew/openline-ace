import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,check=True)
subprocess.run([sys.executable,'scripts/verify_grid.py'],cwd=ROOT,check=True)
subprocess.run([sys.executable,'scripts/verify_freeze.py'],cwd=ROOT,check=True)
print('PASS IS-003 preregistration freeze')
