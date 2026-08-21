from __future__ import annotations

import unittest

from rcdl003.evidence import EXPERIMENT_ROOT, verify_evidence


class FrozenEvidenceTests(unittest.TestCase):
    def test_frozen_evidence_verifies(self) -> None:
        if not (EXPERIMENT_ROOT / "evidence" / "evidence-index.json").is_file():
            self.skipTest("frozen evidence has not been generated yet")
        result = verify_evidence()
        self.assertTrue(result["verified"])
        self.assertFalse(result["promotion_authorized"])


if __name__ == "__main__":
    unittest.main()
