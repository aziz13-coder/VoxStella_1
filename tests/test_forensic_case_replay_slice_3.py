import unittest
from pathlib import Path

from tests.forensic_case_corpus_utils import compare_case_to_forensic_output
from tests.forensic_case_replay_utils import (
    build_forensic_query_string,
    load_forensic_replay_cases,
    make_forensic_replay_app,
)


REPLAY_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "forensic_case_replay_slice_3.json"

CURRENT_COMPARISON_STATUS = {
    "ronnie_lee_bakley": "aligned",
    "marvin_gaye": "aligned",
    "alice_crimmins": "aligned",
    "air_france_447": "misaligned",
    "costa_concordia": "misaligned",
}


class ForensicReplaySliceThreeTests(unittest.TestCase):
    def test_replay_slice_has_expected_cases(self):
        cases = load_forensic_replay_cases(REPLAY_FIXTURE_PATH)
        ids = {case["id"] for case in cases}
        self.assertEqual(
            ids,
            {
                "ronnie_lee_bakley",
                "marvin_gaye",
                "alice_crimmins",
                "air_france_447",
                "costa_concordia",
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
            self.assertEqual(case["metadata_basis"], "source_explicit_prose")
            self.assertEqual(case["metadata_confidence"], "high")
            self.assertTrue(case["source_metadata_note"])

    def test_replay_slice_is_directionally_aligned_against_live_route(self):
        app = make_forensic_replay_app()
        client = app.test_client()

        for case in load_forensic_replay_cases(REPLAY_FIXTURE_PATH):
            with self.subTest(case=case["id"]):
                response = client.get("/api/astro-clock/forensic", query_string=build_forensic_query_string(case))
                self.assertEqual(response.status_code, 200)
                payload = response.get_json() or {}
                self.assertTrue(payload.get("success"))
                comparison = compare_case_to_forensic_output(case, payload)
                self.assertEqual(
                    comparison["status"],
                    CURRENT_COMPARISON_STATUS[case["id"]],
                    msg=f"{case['id']} comparison={comparison} categories={payload.get('categories')} findings={[f.get('title') for f in (payload.get('findings') or [])[:5]]}",
                )


if __name__ == "__main__":
    unittest.main()
