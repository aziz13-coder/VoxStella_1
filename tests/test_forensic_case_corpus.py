import unittest

from tests.forensic_case_corpus_utils import (
    compare_case_to_forensic_output,
    load_forensic_case_corpus,
)


class ForensicCaseCorpusTests(unittest.TestCase):
    def test_corpus_has_starter_sources_and_cases(self):
        corpus = load_forensic_case_corpus()
        self.assertGreaterEqual(len(corpus.get("sources") or []), 3)
        self.assertGreaterEqual(len(corpus.get("cases") or []), 12)

    def test_all_cases_have_required_fields(self):
        corpus = load_forensic_case_corpus()
        for case in corpus.get("cases") or []:
            self.assertTrue(case.get("id"))
            self.assertTrue(case.get("title"))
            self.assertTrue(case.get("book_id"))
            self.assertTrue(case.get("source_file"))
            self.assertTrue(case.get("case_family"))
            self.assertTrue(case.get("expected_primary_axes"))
            self.assertTrue(case.get("execution_tier"))
            self.assertTrue(case.get("chart_capture_status"))

    def test_alignment_helper_marks_clear_match_as_aligned(self):
        corpus = load_forensic_case_corpus()
        case = next(c for c in corpus["cases"] if c["id"] == "scott_peterson")
        forensic_result = {
            "findings": [
                {
                    "title": "Domestic deception pattern",
                    "category": "Deception",
                    "rationale": "Partner involvement with hidden motives and murder indications.",
                }
            ],
            "categories": {"Deception": 3},
        }
        result = compare_case_to_forensic_output(case, forensic_result)
        self.assertEqual(result["status"], "aligned")
        self.assertIn("deception_coverup", result["matched_axes"])
        self.assertIn("domestic_partner_involvement", result["matched_axes"])
        self.assertIn("violence_homicide", result["matched_axes"])

    def test_alignment_helper_marks_contradiction_as_misaligned(self):
        corpus = load_forensic_case_corpus()
        case = next(c for c in corpus["cases"] if c["id"] == "natalie_wood")
        forensic_result = {
            "findings": [
                {
                    "title": "Pure accident signature",
                    "category": "Accident",
                    "rationale": "An accident with no violence or cover-up.",
                }
            ],
            "categories": {"Accident": 2},
        }
        result = compare_case_to_forensic_output(case, forensic_result)
        self.assertEqual(result["status"], "misaligned")
        self.assertIn("accident_or_disaster", result["contradicted_axes"])

    def test_alignment_helper_ignores_negated_contradiction_in_rationale(self):
        corpus = load_forensic_case_corpus()
        case = next(c for c in corpus["cases"] if c["id"] == "natalie_wood")
        forensic_result = {
            "findings": [
                {
                    "title": "Water or drowning signatures are foregrounded",
                    "category": "Water",
                    "rationale": "These signatures point toward violence and water concealment more than a simple accident.",
                }
            ],
            "categories": {"Water": 1, "Violence": 1},
        }
        result = compare_case_to_forensic_output(case, forensic_result)
        self.assertEqual(result["status"], "aligned")
        self.assertNotIn("accident_or_disaster", result["contradicted_axes"])


if __name__ == "__main__":
    unittest.main()
