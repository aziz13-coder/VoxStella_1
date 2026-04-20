import unittest
from pathlib import Path

from tests.forensic_case_corpus_utils import compare_case_to_forensic_output
from tests.forensic_case_replay_utils import load_forensic_replay_cases, make_forensic_replay_app


HOLDOUT_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "forensic_external_journalist_abduction_holdout_cases.json"
)


class JournalistAbductionHoldoutProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = make_forensic_replay_app()
        cls.client = cls.app.test_client()
        cls.cases = {
            case["id"]: case for case in load_forensic_replay_cases(HOLDOUT_FIXTURE_PATH)
        }

    def test_holdout_case_directional_status_matches_frozen_real_world_comparison(self):
        for case_id, case in self.cases.items():
            with self.subTest(case_id=case_id):
                query = dict(case["tested_anchors"][0]["query"])
                response = self.client.get("/api/astro-clock/forensic", query_string=query)
                self.assertEqual(response.status_code, 200, msg=case_id)
                payload = response.get_json() or {}
                self.assertTrue(payload.get("success"), msg=case_id)

                comparison = compare_case_to_forensic_output(case, payload)
                self.assertEqual(
                    comparison["status"],
                    case.get("expected_comparison_status"),
                    msg=(
                        f"comparison={comparison} categories={payload.get('categories')} "
                        f"findings={[f.get('title') for f in (payload.get('findings') or [])[:8]]}"
                    ),
                )


if __name__ == "__main__":
    unittest.main()
