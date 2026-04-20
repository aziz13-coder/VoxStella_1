import unittest

from tests.synastry_content_slice_utils import (
    content_runnable_cases,
    load_synastry_content_slice,
    replay_synastry_content_case,
    summarize_synastry_content_case,
)


class SynastryContentSliceTests(unittest.TestCase):
    def test_content_slice_has_expected_cases_and_lane(self):
        fixture = load_synastry_content_slice()
        ids = {case["id"] for case in fixture.get("cases") or []}

        self.assertEqual(fixture["lane"], "blog_content_only")
        self.assertEqual(
            ids,
            {
                "justin_bieber_selena_gomez",
                "justin_bieber_hailey_bieber",
            },
        )

    def test_content_slice_cases_are_not_calibration_eligible(self):
        fixture = load_synastry_content_slice()
        for case in fixture.get("cases") or []:
            self.assertEqual(case["usage_lane"], "blog_content_only")
            self.assertFalse(case["calibration_eligible"])
            self.assertTrue(case["content_eligible"])
            self.assertEqual(case["validation_recommendation"], "blog_demo_only")

    def test_content_slice_is_runnable_after_chart_capture(self):
        fixture = load_synastry_content_slice()
        runnable_ids = {case["id"] for case in content_runnable_cases(fixture)}
        self.assertEqual(
            runnable_ids,
            {
                "justin_bieber_selena_gomez",
                "justin_bieber_hailey_bieber",
            },
        )

    def test_content_summary_with_chart_capture_is_ready(self):
        fixture = load_synastry_content_slice()
        case = next(c for c in fixture["cases"] if c["id"] == "justin_bieber_selena_gomez")
        report = replay_synastry_content_case(case)

        summary = summarize_synastry_content_case(case, report=report)

        self.assertEqual(summary["report_status"], "ready")
        self.assertEqual(summary["usage_lane"], "blog_content_only")
        self.assertFalse(summary["calibration_eligible"])
        self.assertTrue(summary["category_scores"])
        self.assertTrue(summary["summary_lines"])


if __name__ == "__main__":
    unittest.main()
