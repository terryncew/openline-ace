from __future__ import annotations

import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve()
EXP = HERE.parents[1]
if str(EXP) not in sys.path:
    sys.path.insert(0, str(EXP))

from ap2_context_001.core import Execution, classify, final_mandate_accepts, has_allowed_payees


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "constraints": [
                {
                    "type": "payment.amount_range",
                    "currency": "USD",
                    "min": 5000,
                    "max": 8000,
                }
            ],
            "cnf": {"jwk": {"kty": "EC"}},
        }

    def test_am1_final_mandate_accepts_80_dollars(self):
        self.assertTrue(
            final_mandate_accepts(
                self.payload,
                Execution(8000, "USD", "merchant-camera-store"),
            )
        )

    def test_am1_has_no_allowed_payee_constraint(self):
        self.assertFalse(has_allowed_payees(self.payload))

    def test_above_signed_ceiling_fails(self):
        self.assertFalse(
            final_mandate_accepts(
                self.payload,
                Execution(8001, "USD", "merchant-camera-store"),
            )
        )

    def test_commit_classifies_as_context_gap(self):
        self.assertEqual(
            classify(True, "COMMIT"),
            "VALID_AP2_POISONED_CONTEXT_CROSSES_UNCHANGED_OPENLINE",
        )

    def test_deny_classifies_as_block(self):
        self.assertEqual(
            classify(True, "DENY"),
            "VALID_AP2_POISONED_CONTEXT_BLOCKED_BY_UNCHANGED_OPENLINE",
        )


if __name__ == "__main__":
    unittest.main()
