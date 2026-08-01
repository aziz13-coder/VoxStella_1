import unittest
from pathlib import Path

from tests.forensic_case_replay_utils import load_forensic_replay_cases, make_forensic_replay_app


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "forensic_external_homicide_season3_cases.json"
)


class HomicideSeason3ProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = make_forensic_replay_app()
        cls.client = cls.app.test_client()
        cls.cases = load_forensic_replay_cases(FIXTURE_PATH)

    def test_season_case_probes_resolve_without_route_errors(self):
        for case in self.cases:
            for anchor in case.get("tested_anchors") or []:
                with self.subTest(case_id=case["id"], anchor_id=anchor["id"]):
                    response = self.client.get(
                        "/api/astro-clock/forensic",
                        query_string=dict(anchor["query"]),
                    )
                    self.assertEqual(response.status_code, 200)
                    payload = response.get_json() or {}
                    self.assertTrue(payload.get("success"))

    def test_stable_season_case_category_subsets_hold(self):
        for case in self.cases:
            for anchor in case.get("tested_anchors") or []:
                required = set(anchor.get("required_categories") or [])
                forbidden = set(anchor.get("forbidden_categories") or [])
                if not required and not forbidden:
                    continue
                with self.subTest(case_id=case["id"], anchor_id=anchor["id"]):
                    response = self.client.get(
                        "/api/astro-clock/forensic",
                        query_string=dict(anchor["query"]),
                    )
                    self.assertEqual(response.status_code, 200)
                    payload = response.get_json() or {}
                    self.assertTrue(payload.get("success"))
                    categories = set((payload.get("scoring_categories") or {}).keys())
                    if required:
                        self.assertTrue(required.issubset(categories), msg=payload.get("categories"))
                    for category in forbidden:
                        self.assertNotIn(category, categories, msg=payload.get("categories"))


if __name__ == "__main__":
    unittest.main()
