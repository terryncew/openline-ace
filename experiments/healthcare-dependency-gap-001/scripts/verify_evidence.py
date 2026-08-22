from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    mimic = json.loads((ROOT / "fixtures" / "mimic_iv_demo_2_2_excerpt.json").read_text(encoding="utf-8"))
    lab = mimic["selected_lab"]
    assert lab["labevent_id"] == 415122
    assert lab["subject_id"] == 10035631
    assert lab["hadm_id"] == 21476294
    assert lab["itemid"] == 50971
    assert lab["valuenum"] == 3.7
    assert mimic["lab_dictionary"]["label"] == "Potassium"
    assert all(row["subject_id"] == lab["subject_id"] for row in mimic["same_hospitalization_medication_administrations"])
    assert all(row["hadm_id"] == lab["hadm_id"] for row in mimic["same_hospitalization_medication_administrations"])
    assert "labevent_id" not in mimic["emar_schema"]
    digest = hashlib.sha256((ROOT / "fixtures" / "mimic_iv_demo_2_2_excerpt.json").read_bytes()).hexdigest()
    print("hsr001_evidence_verified mimic_excerpt_sha256=" + digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
