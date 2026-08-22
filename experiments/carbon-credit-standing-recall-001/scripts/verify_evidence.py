from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    result = json.loads((ROOT / "evidence" / "result.json").read_text(encoding="utf-8"))
    if result["status"] != "EXTERNAL_POLICY_REPLAY_PASS":
        raise SystemExit("result is not a passing external-policy replay")

    selective = result["methods"]["selective_reverification"]["metrics"]
    if selective["missed_reopenings"] != 0 or selective["excess_reviews"] != 0:
        raise SystemExit("selective result is not exact")

    if result["policy_authority"] != "NONE":
        raise SystemExit("policy authority escaped")
    if result["runtime_permission"] != "NONE":
        raise SystemExit("runtime permission escaped")

    print("ccr001_evidence_verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
