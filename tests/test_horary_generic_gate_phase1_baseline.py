from __future__ import annotations

import json
import unittest
from pathlib import Path


class HoraryGenericGatePhase1BaselineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo_root = Path(__file__).resolve().parents[1]
        fixture_path = repo_root / "tests" / "fixtures" / "horary_generic_gate_phase1_baseline.json"
        cls.payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    def test_baseline_records_expected_top_level_sections(self):
        self.assertIn("frozen_corpus_totals", self.payload)
        self.assertIn("generic_gate_candidate_queue", self.payload)
        self.assertIn("deferred_exclusions", self.payload)
        self.assertIn("category_doctrine_exclusions", self.payload)

    def test_candidate_queue_is_non_empty_and_contains_phase2_seed_ids(self):
        ids = {entry["id"] for entry in self.payload["generic_gate_candidate_queue"]}
        self.assertIn("masters_program_no_perfection_no", ids)
        self.assertIn("pay_rise_article_spec", ids)
        self.assertGreaterEqual(len(ids), 6)

    def test_deferred_exclusions_match_current_known_open_cases(self):
        ids = {entry["id"] for entry in self.payload["deferred_exclusions"]}
        self.assertEqual(
            ids,
            {
                "will_we_rent_the_house",
                "will_grandfather_survive_this_time",
                "will_barrett_win",
            },
        )


if __name__ == "__main__":
    unittest.main()
