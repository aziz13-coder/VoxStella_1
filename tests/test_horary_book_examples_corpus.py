import json
import unittest
from pathlib import Path


CORPUS_PATH = Path(__file__).resolve().parent / "fixtures" / "horary_book_examples_corpus.json"


class HoraryBookExamplesCorpusTest(unittest.TestCase):
    def setUp(self):
        self.items = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))

    def test_entries_are_unique_and_nontrivial(self):
        self.assertGreaterEqual(len(self.items), 60)
        ids = [item["id"] for item in self.items]
        self.assertEqual(len(ids), len(set(ids)))

    def test_tier_values_are_valid(self):
        allowed_tiers = {
            "tier_1_deterministic_candidate",
            "tier_2_replay_ready_doctrinal_review",
            "tier_3_manual_review_only",
        }
        allowed_statuses = {
            "deterministic_replay_candidate",
            "replay_ready_doctrinal_review",
            "manual_review_only",
        }
        for item in self.items:
            self.assertIn(item["tier"], allowed_tiers)
            self.assertIn(item["replay_status"], allowed_statuses)

    def test_header_metadata_is_present_for_current_book_cases(self):
        for item in self.items:
            self.assertTrue(item["has_explicit_date"])
            self.assertTrue(item["has_explicit_time"])
            self.assertTrue(item["has_explicit_location"])

    def test_split_contains_both_deterministic_and_review_cases(self):
        tier1 = sum(1 for item in self.items if item["tier"] == "tier_1_deterministic_candidate")
        tier2 = sum(1 for item in self.items if item["tier"] == "tier_2_replay_ready_doctrinal_review")
        self.assertGreaterEqual(tier1, 10)
        self.assertGreaterEqual(tier2, 20)


if __name__ == "__main__":
    unittest.main()
