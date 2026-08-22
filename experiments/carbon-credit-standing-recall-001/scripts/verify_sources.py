from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str) -> dict[str, object]:
    return json.loads((ROOT / "sources" / name).read_text(encoding="utf-8"))


def main() -> int:
    cohort = load("verra_cquest_completed_qcr.json")
    rows = cohort["rows"]
    if len(rows) != cohort["completed_project_count"]:
        raise SystemExit("completed project count mismatch")

    total = sum(int(row["compensated"]) for row in rows)
    if total != int(cohort["published_total_compensated"]):
        raise SystemExit(f"compensated total mismatch: {total}")

    for row in rows:
        issued = int(row["issued"])
        revised = int(row["revised"])
        compensated = int(row["compensated"])
        if issued > 0 and issued - revised != compensated:
            raise SystemExit(
                "row arithmetic mismatch for project "
                + str(row["project_id"])
            )
        if issued == 0 and compensated != 0:
            raise SystemExit(
                "zero-issuance row has compensation for project "
                + str(row["project_id"])
            )

    target = next(row for row in rows if int(row["project_id"]) == 2372)
    expected = {
        "issued": 4_444_642,
        "revised": 2_409_500,
        "compensated": 2_035_142,
    }
    for key, value in expected.items():
        if int(target[key]) != value:
            raise SystemExit(f"project 2372 {key} mismatch")

    ledger = load("source_ledger.json")
    boeing = next(
        source for source in ledger["sources"]
        if source["source_id"] == "boeing-cdp-2024"
    )
    if int(boeing["project_2372_retired_vcu_count_from_ranges"]) != 75_034:
        raise SystemExit("Boeing project 2372 retirement range count mismatch")

    print(
        "ccr001_source_verification_pass "
        f"rows={len(rows)} compensated_total={total}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
