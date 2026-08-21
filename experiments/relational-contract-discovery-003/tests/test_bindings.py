from __future__ import annotations

import sys
import unittest

from rcdl003.bindings import verify_frozen_bindings


class BindingTests(unittest.TestCase):
    def test_frozen_bindings_verify(self) -> None:
        result = verify_frozen_bindings().to_dict()
        self.assertTrue(result["verified"])
        self.assertEqual(result["clause_count"], 5)
        self.assertEqual(result["source_trace_count"], 10)
        self.assertEqual(result["engine_file_count"], 9)
        self.assertNotEqual(
            result["source_implementation_sha256"],
            result["replica_implementation_sha256"],
        )

    def test_boundary_does_not_claim_independent_lab(self) -> None:
        result = verify_frozen_bindings().to_dict()
        self.assertTrue(result["code_path_independent"])
        self.assertFalse(result["independent_developer_or_lab"])

    def test_source_runtime_package_is_not_imported(self) -> None:
        verify_frozen_bindings()
        self.assertNotIn("rcdl002", sys.modules)


if __name__ == "__main__":
    unittest.main()
