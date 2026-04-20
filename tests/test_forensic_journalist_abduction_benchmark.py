import unittest
from pathlib import Path

from tests.forensic_case_corpus_utils import compare_case_to_forensic_output
from tests.forensic_case_replay_utils import (
    build_forensic_query_string,
    load_forensic_replay_cases,
    make_forensic_replay_app,
)


BENCHMARK_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "forensic_external_journalist_abduction_candidates.json"
)


class JournalistAbductionBenchmarkTests(unittest.TestCase):
    def _assert_case_is_directionally_aligned(self, case_id, query_override=None):
        app = make_forensic_replay_app()
        client = app.test_client()
        cases = {
            case["id"]: case for case in load_forensic_replay_cases(BENCHMARK_FIXTURE_PATH)
        }
        case = cases[case_id]
        query = dict(query_override or case["tested_anchors"][0]["query"])

        response = client.get("/api/astro-clock/forensic", query_string=query)
        self.assertEqual(response.status_code, 200)
        payload = response.get_json() or {}
        self.assertTrue(payload.get("success"))

        comparison = compare_case_to_forensic_output(case, payload)
        self.assertEqual(
            comparison["status"],
            "aligned",
            msg=f"comparison={comparison} categories={payload.get('categories')} findings={[f.get('title') for f in (payload.get('findings') or [])[:6]]}",
        )

    def test_rory_carroll_anchor_is_directionally_aligned_against_live_route(self):
        self._assert_case_is_directionally_aligned("rory_carroll_sadr_city_abduction")

    def test_jill_carroll_anchor_is_directionally_aligned_against_live_route(self):
        self._assert_case_is_directionally_aligned("jill_carroll_adil_abduction")

    def test_giuliana_sgrena_anchor_is_directionally_aligned_against_live_route(self):
        self._assert_case_is_directionally_aligned("giuliana_sgrena_baghdad_abduction")

    def test_james_brandon_anchor_is_directionally_aligned_against_live_route(self):
        self._assert_case_is_directionally_aligned("james_brandon_basra_abduction")

    def test_alan_johnston_anchor_is_directionally_aligned_against_live_route(self):
        self._assert_case_is_directionally_aligned("alan_johnston_gaza_abduction")

    def test_centanni_wiig_anchor_is_directionally_aligned_against_live_route(self):
        self._assert_case_is_directionally_aligned("centanni_wiig_gaza_abduction")


if __name__ == "__main__":
    unittest.main()
