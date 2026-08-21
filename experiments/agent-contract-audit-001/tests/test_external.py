import json
import unittest

from aca001.conformance import fixture_candidates
from aca001.external import RESULT_PROTOCOL, build_request, parse_result


class ExternalProtocolTests(unittest.TestCase):
    def test_request_has_no_authority(self):
        req = build_request(
            fixture_candidates()[0],
            arm="active",
            pair_id="p1",
            task_id="t1",
            seed=7,
        )
        self.assertEqual(req["authority"], "NONE")
        self.assertNotIn("expected_standing", req)

    def test_result_binding_is_receiver_checked(self):
        req = build_request(
            fixture_candidates()[0],
            arm="active",
            pair_id="p1",
            task_id="t1",
            seed=7,
        )
        value = {
            "protocol": RESULT_PROTOCOL,
            "candidate_id": req["candidate_id"],
            "pair_id": "wrong",
            "task_id": req["task_id"],
            "seed": req["seed"],
            "arm": req["arm"],
            "verifier": {"id": "original", "success": False},
        }
        with self.assertRaises(ValueError):
            parse_result(req, json.dumps(value).encode())

    def test_wrapper_status_does_not_replace_verifier(self):
        req = build_request(
            fixture_candidates()[3],
            arm="active",
            pair_id="p1",
            task_id="t1",
            seed=7,
        )
        value = {
            "protocol": RESULT_PROTOCOL,
            "candidate_id": req["candidate_id"],
            "pair_id": req["pair_id"],
            "task_id": req["task_id"],
            "seed": req["seed"],
            "arm": req["arm"],
            "runner_status": "wrapper_blocked",
            "verifier": {"id": "original", "success": True},
        }
        result = parse_result(req, json.dumps(value).encode())
        self.assertTrue(result.verifier_success)
        self.assertEqual(result.runner_status, "wrapper_blocked")


if __name__ == "__main__":
    unittest.main()
