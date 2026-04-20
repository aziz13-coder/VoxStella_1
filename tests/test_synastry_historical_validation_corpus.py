import unittest

from tests.synastry_historical_validation_utils import (
    compare_case_to_synastry_output,
    load_synastry_historical_validation_corpus,
    runnable_cases,
    score_to_band,
)


class SynastryHistoricalValidationCorpusTests(unittest.TestCase):
    def test_corpus_has_sources_and_starter_cases(self):
        corpus = load_synastry_historical_validation_corpus()
        self.assertGreaterEqual(len(corpus.get("sources") or []), 3)
        self.assertGreaterEqual(len(corpus.get("cases") or []), 10)

    def test_all_cases_have_required_fields(self):
        corpus = load_synastry_historical_validation_corpus()
        for case in corpus.get("cases") or []:
            self.assertTrue(case.get("id"))
            self.assertTrue(case.get("title"))
            self.assertTrue(case.get("partner_a"))
            self.assertTrue(case.get("partner_b"))
            self.assertTrue(case.get("relationship_type"))
            self.assertTrue(case.get("public_outcome_summary"))
            self.assertTrue(case.get("execution_tier"))
            self.assertTrue(case.get("chart_capture_status"))
            self.assertTrue(case.get("comparison_status"))
            self.assertTrue(case.get("expected_dimensions"))

    def test_score_to_band_uses_stable_thresholds(self):
        self.assertEqual(score_to_band(5), 0)
        self.assertEqual(score_to_band(25), 1)
        self.assertEqual(score_to_band(45), 2)
        self.assertEqual(score_to_band(60), 3)
        self.assertEqual(score_to_band(75), 4)
        self.assertEqual(score_to_band(90), 5)

    def test_comparison_helper_marks_expected_high_attachment_case_as_aligned(self):
        corpus = load_synastry_historical_validation_corpus()
        case = next(c for c in corpus["cases"] if c["id"] == "paul_newman_joanne_woodward")
        synastry_report = {
            "categories": [
                {"id": "overall", "score": 80},
                {"id": "resonance", "score": 66},
                {"id": "communication", "score": 58},
                {"id": "attraction", "score": 64},
                {"id": "compatibility", "score": 74},
                {"id": "attachment", "score": 88},
                {"id": "growth", "score": 55},
                {"id": "friction", "score": 28},
                {"id": "burden", "score": 18}
            ]
        }
        result = compare_case_to_synastry_output(case, synastry_report)
        self.assertEqual(result["status"], "aligned")
        self.assertIn("attachment", result["matched_dimensions"])
        self.assertIn("compatibility", result["matched_dimensions"])

    def test_comparison_helper_marks_high_burden_case_as_misaligned_when_negative_dimensions_are_too_low(self):
        corpus = load_synastry_historical_validation_corpus()
        case = next(c for c in corpus["cases"] if c["id"] == "charles_diana")
        synastry_report = {
            "categories": [
                {"id": "overall", "score": 71},
                {"id": "resonance", "score": 70},
                {"id": "communication", "score": 68},
                {"id": "attraction", "score": 80},
                {"id": "compatibility", "score": 72},
                {"id": "attachment", "score": 77},
                {"id": "growth", "score": 63},
                {"id": "friction", "score": 20},
                {"id": "burden", "score": 18}
            ]
        }
        result = compare_case_to_synastry_output(case, synastry_report)
        self.assertEqual(result["status"], "misaligned")
        self.assertIn("burden", result["missed_primary_dimensions"])
        self.assertIn("friction", result["missed_primary_dimensions"])

    def test_runnable_cases_starts_empty_until_chart_data_is_captured(self):
        corpus = load_synastry_historical_validation_corpus()
        self.assertEqual(runnable_cases(corpus), [])

    def test_high_traffic_bieber_cases_are_classified_as_non_calibration(self):
        corpus = load_synastry_historical_validation_corpus()
        selena_case = next(c for c in corpus["cases"] if c["id"] == "justin_bieber_selena_gomez")
        hailey_case = next(c for c in corpus["cases"] if c["id"] == "justin_bieber_hailey_bieber")

        self.assertEqual(selena_case["validation_recommendation"], "blog_demo_only")
        self.assertEqual(selena_case["comparison_status"], "manual_review")
        self.assertEqual(selena_case["execution_tier"], "tier_3_manual_review")
        self.assertEqual(selena_case["usage_lane"], "blog_content_only")
        self.assertFalse(selena_case["calibration_eligible"])
        self.assertEqual(selena_case["birth_data_confidence"], "B")

        self.assertEqual(hailey_case["validation_recommendation"], "blog_demo_only")
        self.assertEqual(hailey_case["execution_tier"], "tier_3_manual_review")
        self.assertEqual(hailey_case["usage_lane"], "blog_content_only")
        self.assertFalse(hailey_case["calibration_eligible"])
        self.assertEqual(hailey_case["birth_data_confidence"], "C")

    def test_slice_2_cases_are_promoted_to_replay_ready_status(self):
        corpus = load_synastry_historical_validation_corpus()
        expected = {
            "frida_kahlo_diego_rivera": ("AA/DD", "partially_aligned"),
            "sid_nancy": ("A/B", "aligned"),
            "elizabeth_taylor_richard_burton": ("AA/DD", "aligned"),
        }

        for case_id, (confidence, status) in expected.items():
            case = next(c for c in corpus["cases"] if c["id"] == case_id)
            self.assertEqual(case["execution_tier"], "tier_2_replay_ready")
            self.assertEqual(case["chart_capture_status"], "captured_replay_slice_2")
            self.assertEqual(case["comparison_status"], status)
            self.assertEqual(case["birth_data_confidence"], confidence)
            self.assertTrue(case["source_references"])
            self.assertTrue(case["replay_fixture"].endswith("synastry_historical_replay_slice_2.json"))

    def test_slice_3_cases_are_promoted_to_replay_ready_status(self):
        corpus = load_synastry_historical_validation_corpus()
        expected = {
            "frank_sinatra_ava_gardner": ("A/AA", "aligned"),
            "sartre_beauvoir": ("AA/AA", "aligned"),
        }

        for case_id, (confidence, status) in expected.items():
            case = next(c for c in corpus["cases"] if c["id"] == case_id)
            self.assertEqual(case["execution_tier"], "tier_2_replay_ready")
            self.assertEqual(case["chart_capture_status"], "captured_replay_slice_3")
            self.assertEqual(case["comparison_status"], status)
            self.assertEqual(case["birth_data_confidence"], confidence)
            self.assertTrue(case["source_references"])
            self.assertTrue(case["replay_fixture"].endswith("synastry_historical_replay_slice_3.json"))


if __name__ == "__main__":
    unittest.main()
