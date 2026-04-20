import unittest
from pathlib import Path

from tests.forensic_case_corpus_utils import compare_case_to_forensic_output
from tests.forensic_case_replay_utils import (
    build_forensic_query_string,
    load_forensic_replay_cases,
    make_forensic_replay_app,
)


REPLAY_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "forensic_external_replay_slice_2.json"


class ForensicExternalReplaySliceTwoTests(unittest.TestCase):
    def test_replay_slice_has_expected_case(self):
        cases = load_forensic_replay_cases(REPLAY_FIXTURE_PATH)
        self.assertEqual([case["id"] for case in cases], ["mlk_assassination"])

    def test_metadata_basis_is_tracked(self):
        case = load_forensic_replay_cases(REPLAY_FIXTURE_PATH)[0]
        self.assertEqual(case["metadata_basis"], "official_archival_exact_shot_time")
        self.assertEqual(case["metadata_confidence"], "high")
        self.assertTrue(case["source_metadata_note"])

    def test_replay_slice_is_directionally_aligned_against_live_route(self):
        app = make_forensic_replay_app()
        client = app.test_client()
        case = load_forensic_replay_cases(REPLAY_FIXTURE_PATH)[0]

        response = client.get("/api/astro-clock/forensic", query_string=build_forensic_query_string(case))
        self.assertEqual(response.status_code, 200)
        payload = response.get_json() or {}
        self.assertTrue(payload.get("success"))
        comparison = compare_case_to_forensic_output(case, payload)
        self.assertEqual(
            comparison["status"],
            "aligned",
            msg=f"{case['id']} comparison={comparison} categories={payload.get('categories')} findings={[f.get('title') for f in (payload.get('findings') or [])[:6]]}",
        )


if __name__ == "__main__":
    unittest.main()
