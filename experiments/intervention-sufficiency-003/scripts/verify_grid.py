from pathlib import Path
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from is003.grid import load_grid, verify_grid

grid = load_grid()
errors = verify_grid(grid)
expected = (ROOT / 'GRID.sha256').read_text().split()[0]
actual = hashlib.sha256((ROOT / 'GRID.json').read_bytes()).hexdigest()
if expected != actual:
    errors.append(f'GRID hash mismatch: {actual}')
if errors:
    raise SystemExit('\n'.join(errors))
print(f'PASS grid_sha256={actual} contexts={len(grid["contexts"])} pilot_overlap=0')
