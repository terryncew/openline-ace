import unittest
from datetime import datetime, timedelta, timezone

from sld002.core import build_case, evaluate


def iso(hour):
    return (
        datetime(2025, 1, 1, tzinfo=timezone.utc)
        + timedelta(hours=hour)
    ).isoformat().replace("+00:00", "Z")


def candidate(number=1, stratum="terminal_unmerged"):
    return {
        "repository": "example/repo",
        "number": number,
        "stratum": stratum,
        "closed_at": iso(100),
        "history_truncated": False,
    }


def commit(commit_sha, hour):
    return {
        "sha": commit_sha,
        "commit": {"committer": {"date": iso(hour)}},
    }


def review(review_id, state, commit_sha, hour):
    return {
        "id": review_id,
        "state": state,
        "commit_id": commit_sha,
        "submitted_at": iso(hour),
    }


class BuildCaseTests(unittest.TestCase):
    def test_reopen_earns_no_loss_credit_until_changes_requested(self):
        case = build_case(
            candidate(),
            [
                review(1, "APPROVED", "a", 10),
                review(2, "CHANGES_REQUESTED", "b", 30),
            ],
            [commit("a", 5), commit("b", 20)],
        )
        self.assertTrue(case["eligible"])
        self.assertEqual(case["change"]["committed_at"], iso(20))
        self.assertEqual(case["standing_loss_at"], iso(30))

    def test_approved_reverification_retains_standing(self):
        case = build_case(
            candidate(stratum="merged_control"),
            [review(1, "APPROVED", "a", 10), review(2, "APPROVED", "b", 30)],
            [commit("a", 5), commit("b", 20)],
        )
        self.assertEqual(case["standing_after_reverify"], "VALID")
        self.assertIsNone(case["standing_loss_at"])

    def test_no_rereview_is_unresolved_not_lost(self):
        case = build_case(
            candidate(),
            [review(1, "APPROVED", "a", 10)],
            [commit("a", 5), commit("b", 20)],
        )
        self.assertTrue(case["eligible"])
        self.assertEqual(case["standing_after_reverify"], "UNRESOLVED")

    def test_review_after_close_cannot_rescue_or_kill(self):
        case = build_case(
            candidate(),
            [
                review(1, "APPROVED", "a", 10),
                review(2, "CHANGES_REQUESTED", "b", 110),
            ],
            [commit("a", 5), commit("b", 20)],
        )
        self.assertEqual(case["standing_after_reverify"], "UNRESOLVED")

    def test_truncated_history_is_ineligible(self):
        value = candidate()
        value["history_truncated"] = True
        case = build_case(value, [], [])
        self.assertFalse(case["eligible"])
        self.assertEqual(case["ineligibility_reason"], "history_truncated")


class EvaluateTests(unittest.TestCase):
    def setUp(self):
        self.prereg = {
            "data_boundary": "test",
            "minimum_terminal_cases": 4,
            "minimum_detected_terminal_cases": 3,
            "minimum_valid_reverification_controls": 4,
            "minimum_repositories_with_eligible_cases": 2,
            "minimum_terminal_detection_fraction": 0.5,
            "minimum_positive_lead_fraction": 0.75,
            "minimum_median_lead_hours": 6.0,
            "naive_false_invalidation_ratio_max": 0.25,
            "ttl_hours": 12.0,
        }

    def make_case(
        self,
        number,
        repo,
        stratum,
        loss_hour=None,
        reverify="VALID",
    ):
        value = {
            "case_id": f"{repo}#{number}",
            "repository": repo,
            "number": number,
            "stratum": stratum,
            "eligible": True,
            "headline_at": iso(100),
            "baseline_approval": {"submitted_at": iso(10)},
            "change": {"committed_at": iso(20)},
            "standing_after_reverify": reverify,
            "standing_loss_at": None,
            "reverify": None,
        }
        if reverify == "VALID":
            value["reverify"] = {
                "state": "APPROVED",
                "submitted_at": iso(30),
            }
        elif reverify == "LOST":
            value["reverify"] = {
                "state": "CHANGES_REQUESTED",
                "submitted_at": iso(loss_hour),
            }
            value["standing_loss_at"] = iso(loss_hour)
        return value

    def advantage_rows(self):
        rows = [
            self.make_case(1, "a/r", "terminal_unmerged", 30, "LOST"),
            self.make_case(2, "a/r", "terminal_unmerged", 40, "LOST"),
            self.make_case(3, "b/r", "terminal_unmerged", 50, "LOST"),
            self.make_case(4, "b/r", "terminal_unmerged", None, "UNRESOLVED"),
        ]
        rows += [
            self.make_case(
                number + 10,
                "a/r" if number % 2 == 0 else "b/r",
                "merged_control",
                None,
                "VALID",
            )
            for number in range(4)
        ]
        return rows

    def test_advantage_can_win_without_beating_naive_timestamp(self):
        result = evaluate(self.advantage_rows(), self.prereg)
        self.assertEqual(
            result["verdict"],
            "EXTERNAL_STANDING_LOSS_LEAD_TIME_ADVANTAGE",
        )
        self.assertGreater(
            result["naive_diff"]["median_terminal_lead_hours"],
            result["olp"]["median_detected_lead_hours"],
        )
        self.assertEqual(
            result["olp"]["unnecessary_invalidation_rate_on_valid_controls"],
            0.0,
        )
        self.assertEqual(
            result["naive_diff"][
                "unnecessary_invalidation_rate_on_valid_controls"
            ],
            1.0,
        )

    def test_low_coverage_loses(self):
        rows = [
            self.make_case(1, "a/r", "terminal_unmerged", 30, "LOST"),
            self.make_case(2, "a/r", "terminal_unmerged", None, "UNRESOLVED"),
            self.make_case(3, "b/r", "terminal_unmerged", None, "UNRESOLVED"),
            self.make_case(4, "b/r", "terminal_unmerged", None, "UNRESOLVED"),
        ]
        rows += [
            self.make_case(
                number + 10,
                "a/r" if number % 2 == 0 else "b/r",
                "merged_control",
                None,
                "VALID",
            )
            for number in range(4)
        ]
        self.prereg["minimum_detected_terminal_cases"] = 1
        result = evaluate(rows, self.prereg)
        self.assertEqual(
            result["verdict"],
            "NO_EXTERNAL_STANDING_LOSS_ADVANTAGE",
        )

    def test_data_insufficient(self):
        result = evaluate(
            [self.make_case(1, "a/r", "terminal_unmerged", 30, "LOST")],
            self.prereg,
        )
        self.assertEqual(result["verdict"], "DATA_INSUFFICIENT")

    def test_source_failure_is_explicit(self):
        result = evaluate([], self.prereg, source_access_ok=False)
        self.assertEqual(result["verdict"], "SOURCE_ACCESS_FAILED")

    def test_merged_after_loss_is_recovery_not_false_control(self):
        rows = self.advantage_rows()
        rows.append(
            self.make_case(99, "b/r", "merged_control", 45, "LOST")
        )
        result = evaluate(rows, self.prereg)
        self.assertIn(
            "b/r#99",
            result["coverage_limits"]["merged_after_intermediate_loss"],
        )
        self.assertEqual(
            result["olp"]["unnecessary_invalidation_rate_on_valid_controls"],
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
