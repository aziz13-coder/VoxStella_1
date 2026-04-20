import unittest

from tests.forensic_case_replay_utils import build_forensic_query_string, load_forensic_replay_cases


class ForensicReplaySliceOneTests(unittest.TestCase):
    def test_replay_slice_has_expected_cases(self):
        cases = load_forensic_replay_cases()
        ids = {case["id"] for case in cases}
        self.assertEqual(
            ids,
            {
                "lindbergh_kidnapping",
                "phil_hartman",
                "natalie_wood",
                "scott_peterson",
                "jonbenet_ramsey",
                "susan_smith",
            },
        )

    def test_replay_queries_are_complete(self):
        for case in load_forensic_replay_cases():
            query = build_forensic_query_string(case)
            self.assertEqual(query["mode"], "manual")
            self.assertTrue(query["datetime"])
            self.assertTrue(query["location"])
            self.assertTrue(query["timezone"])
            self.assertTrue(query["house_system_code"])

    def test_metadata_basis_is_tracked(self):
        for case in load_forensic_replay_cases():
            self.assertIn(case["metadata_basis"], {"source_explicit_prose", "source_ocr_chart", "mixed"})
            self.assertIn(case["metadata_confidence"], {"high", "medium", "low"})
            self.assertTrue(case["source_metadata_note"])


if __name__ == "__main__":
    unittest.main()
