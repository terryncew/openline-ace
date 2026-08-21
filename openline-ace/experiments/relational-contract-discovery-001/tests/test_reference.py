from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from rcdl.reference import (
    DEFAULT_RECORD,
    ReferenceVerificationError,
    load_reference_record,
    verify_reference,
)


class OfficialReferenceTests(unittest.TestCase):
    def test_pinned_official_spec_matches_both_hashes(self) -> None:
        result = verify_reference()
        self.assertEqual(
            result.content_sha256,
            "2cf54dbedc5d81f3b108596a24644279a3bbc94cc0980108ee51590c7461cc3b",
        )
        self.assertEqual(
            result.git_blob_sha1,
            "ce9fc1573b576b15c12e4c0dea337fce41be720a",
        )
        self.assertEqual(result.execution_binding, "PROPERTY_MAPPING_ONLY")
        self.assertEqual(result.tlc_execution, "NOT_RUN")

    def test_reference_maps_exact_oracle_properties(self) -> None:
        record = load_reference_record()
        self.assertEqual(
            record["mapped_safety_properties"],
            [
                "election_safety",
                "leader_completeness",
                "log_matching",
                "state_machine_safety",
            ],
        )

    def test_reference_content_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            shutil.copy2(DEFAULT_RECORD, target / DEFAULT_RECORD.name)
            source = DEFAULT_RECORD.parent / "raft.tla"
            shutil.copy2(source, target / "raft.tla")
            with (target / "raft.tla").open("ab") as handle:
                handle.write(b"\n\\* tamper\n")
            with self.assertRaises(ReferenceVerificationError):
                verify_reference(target / DEFAULT_RECORD.name)


if __name__ == "__main__":
    unittest.main()
