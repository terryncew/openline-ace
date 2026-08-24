import json
from .evaluator import run_all

print(json.dumps(run_all(), indent=2, sort_keys=True))
