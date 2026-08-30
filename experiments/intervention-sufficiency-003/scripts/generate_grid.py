from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from is003.grid import regenerate_contexts

grid = json.loads((ROOT / 'GRID.json').read_text())
grid['contexts'] = regenerate_contexts()
print(json.dumps(grid, indent=2, sort_keys=True))
