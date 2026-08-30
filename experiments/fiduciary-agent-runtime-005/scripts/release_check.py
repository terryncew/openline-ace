from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
for script in ['verify_freeze.py','verify_upstream_membrane.py','run_controls.py']:
 subprocess.run([sys.executable,str(ROOT/'scripts'/script)],cwd=ROOT,check=True)
subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py'],cwd=ROOT,check=True)
print('PASS FAR-005 release check')
