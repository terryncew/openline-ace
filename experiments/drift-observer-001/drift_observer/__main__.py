from __future__ import annotations

import json
from pathlib import Path

from .fixture import run_fixture


def main() -> int:
    result = run_fixture()
    out = Path("evidence/result.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    print("OPENLINE DRIFT OBSERVER 001")
    print("delta_hol = dependency-aware verified-reference displacement")
    print()
    for name, observation in result["scenarios"].items():
        impacts = {
            item["claim_id"]: item["disposition"]
            for item in observation["claim_impacts"]
        }
        print(
            f"{name:<18} {observation['status']:<28} "
            f"crossed={observation['crossed_dimensions']} impacts={impacts}"
        )
    print()
    print("Verdict:", result["status"])
    print("Policy authority: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
