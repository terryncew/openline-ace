from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rcdl006.tournament import run_tournament
from rcdl006.verification import verify_manifest, verify_projection


class TournamentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.output = Path(self.tmp.name) / "out"
        self.summary = run_tournament(self.output)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_expected_row_count(self) -> None:
        self.assertEqual(self.summary["result_rows"], 384)

    def test_computed_verdict_is_parity(self) -> None:
        self.assertEqual(self.summary["scientific_verdict"], "HELD_OUT_MECHANISM_CAUSAL_PARITY")
        self.assertEqual(self.summary["symbolic"]["accuracy_ppm"], 1_000_000)
        self.assertEqual(self.summary["baseline"]["accuracy_ppm"], 1_000_000)

    def test_manifest_and_projection_verify(self) -> None:
        self.assertTrue(verify_manifest(self.output / "heldout-mechanism-manifest.json").document)
        self.assertTrue(verify_projection(self.output / "verified-handoff-projection.json").document)

    def test_result_policy_balance(self) -> None:
        records = [json.loads(line) for line in (self.output / "heldout-mechanism-results.jsonl").read_text().splitlines()]
        self.assertEqual(sum(item["policy"] == "symbolic-rcdl" for item in records), 192)
        self.assertEqual(sum(item["policy"] == "learned-signature-baseline" for item in records), 192)

    def test_each_record_has_three_queries_and_equal_energy(self) -> None:
        records = [json.loads(line) for line in (self.output / "heldout-mechanism-results.jsonl").read_text().splitlines()]
        for item in records:
            transcript = item["query_transcript"]
            self.assertEqual(transcript["query_count"], 3)
            self.assertEqual(transcript["active"]["energy"], transcript["sham"]["energy"])

    def test_result_tampering_is_rejected(self) -> None:
        path = self.output / "heldout-mechanism-results.jsonl"
        payload = bytearray(path.read_bytes())
        payload[5] ^= 1
        path.write_bytes(bytes(payload))
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            verify_manifest(self.output / "heldout-mechanism-manifest.json")

    def test_sidecar_tampering_is_rejected(self) -> None:
        sidecar = self.output / "heldout-mechanism-manifest.json.sha256"
        sidecar.write_text("0" * 64 + "  heldout-mechanism-manifest.json\n")
        with self.assertRaisesRegex(ValueError, "sidecar mismatch"):
            verify_manifest(self.output / "heldout-mechanism-manifest.json")

    def test_nonempty_output_requires_force(self) -> None:
        with self.assertRaisesRegex(ValueError, "not empty"):
            run_tournament(self.output)

    def test_deterministic_replay(self) -> None:
        other = Path(self.tmp.name) / "other"
        second = run_tournament(other)
        self.assertEqual(self.summary["results_digest"], second["results_digest"])
        self.assertEqual(self.summary["manifest_digest"], second["manifest_digest"])


if __name__ == "__main__":
    unittest.main()
