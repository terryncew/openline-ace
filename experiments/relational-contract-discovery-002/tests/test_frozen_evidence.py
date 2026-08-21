from __future__ import annotations

import unittest
from pathlib import Path

from rcdl002.evidence import EXPERIMENT_ROOT, verify_evidence


class FrozenEvidenceTests(unittest.TestCase):
    def test_frozen_evidence_and_source_binding(self) -> None:
        if not (Path(EXPERIMENT_ROOT) / "evidence" / "evidence-index.json").is_file():
            self.skipTest("frozen evidence is generated after source tests pass")
        result = verify_evidence()
        self.assertTrue(result["verified"])
        self.assertFalse(result["promotion_authorized"])


if __name__ == "__main__":
    unittest.main()
