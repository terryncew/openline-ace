from __future__ import annotations

import unittest

from rcdl.evidence import verify_evidence


class FrozenEvidenceTests(unittest.TestCase):
    def test_frozen_evidence_and_source_binding(self) -> None:
        result = verify_evidence()
        self.assertTrue(result["verified"])
        self.assertFalse(result["promotion_authorized"])


if __name__ == "__main__":
    unittest.main()
