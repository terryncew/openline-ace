import json
import tempfile
import unittest
from pathlib import Path

from aca001.evidence import build_evidence, verify_evidence


class EvidenceTests(unittest.TestCase):
    def test_build_and_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            build_evidence(out)
            result = verify_evidence(out)
            self.assertEqual(result["status"], "VERIFIED")
            self.assertEqual(result["verdict"], "CONFORMANCE_PASS_EXTERNAL_UNRUN")

    def test_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            build_evidence(out)
            path = out / "contract-grades.json"
            path.write_text(path.read_text() + " ", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                verify_evidence(out)


if __name__ == "__main__":
    unittest.main()
