from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcdl007.evidence import build_evidence, verify_evidence


class EvidenceTests(unittest.TestCase):
    def test_build_and_verify(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            result = build_evidence(output)
            self.assertEqual(result["verdict"], "PRE_ADJUDICATION_CAUSAL_PARITY")
            verify_evidence(output)

    def test_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            build_evidence(output)
            path = output / "evaluation-results.jsonl"
            path.write_text(path.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "evidence mismatch"):
                verify_evidence(output)


if __name__ == "__main__":
    unittest.main()
