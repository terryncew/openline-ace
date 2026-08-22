import subprocess,sys
from pathlib import Path
expected="ae6a8403e272733e9996ef59990880330496177f"; repo=Path(sys.argv[1]); got=subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD"],text=True).strip()
if got!=expected: raise SystemExit(f"wrong pin: {got}")
t=(repo/"readme.md").read_text(errors="replace")
for n in ("Current version only supports low-level development","LowCmd","LowState","SportModeState"):
    if n not in t: raise SystemExit(f"missing upstream marker: {n}")
print("UNITREE_PIN_VERIFIED",got)
