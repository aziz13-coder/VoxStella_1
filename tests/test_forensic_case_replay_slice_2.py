import unittest
from pathlib import Path

from tests.forensic_case_replay_utils import build_forensic_query_string, load_forensic_replay_cases


REPLAY_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "forensic_case_replay_slice_2.json"


class ForensicReplaySliceTwoTests(unittest.TestCase):
    def test_replay_slice_has_expected_cases(self):
        cases = load_forensic_replay_cases(REPLAY_FIXTURE_PATH)
        ids = {case["id"] for case in cases}
        self.assertEqual(
            ids,
            {
                "andrea_yates",
                "darlie_routier",
                "lizzie_borden",
                "menendez_brothers",
                "john_list",
                "amityville_defeo",
                "bob_crane",
                "gianni_versace",
            },
        )

    def test_replay_queries_are_complete(self):
        for case in load_forensic_replay_cases(REPLAY_FIXTURE_PATH):
            query = build_forensic_query_string(case)
            self.assertEqual(query["mode"], "manual")
            self.assertTrue(query["datetime"])
            self.assertTrue(query["location"])
            self.assertTrue(query["timezone"])
            self.assertTrue(query["house_system_code"])

    def test_metadata_basis_is_tracked(self):
        for case in load_forensic_replay_cases(REPLAY_FIXTURE_PATH):
            self.assertIn(case["metadata_basis"], {"source_explicit_prose", "source_ocr_chart", "mixed"})
            self.assertIn(case["metadata_confidence"], {"high", "medium", "low"})
            self.assertTrue(case["source_metadata_note"])


if __name__ == "__main__":
    unittest.main()
