import unittest
from pathlib import Path

from tests.forensic_case_replay_utils import load_forensic_replay_cases, make_forensic_replay_app


PROBE_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "forensic_external_homicide_documentary_probes.json"
)


class HomicideDocumentaryProbeSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = make_forensic_replay_app()
        cls.client = cls.app.test_client()
        cls.case = load_forensic_replay_cases(PROBE_FIXTURE_PATH)[0]

    def test_party_monster_probe_anchors_resolve_without_route_errors(self):
        for anchor in self.case.get("tested_anchors") or []:
            with self.subTest(anchor_id=anchor["id"]):
                response = self.client.get(
                    "/api/astro-clock/forensic",
                    query_string=dict(anchor["query"]),
                )
                self.assertEqual(response.status_code, 200)
                payload = response.get_json() or {}
                self.assertTrue(payload.get("success"))

    def test_party_monster_best_anchors_surface_known_person_violence_and_not_disaster(self):
        expected = {
            "joey_2016_11_13_0650": {"Violence", "Associates"},
            "joey_2016_11_13_0700": {"Violence", "Associates"},
        }

        for anchor in self.case.get("tested_anchors") or []:
            anchor_id = anchor["id"]
            if anchor_id not in expected:
                continue
            with self.subTest(anchor_id=anchor_id):
                response = self.client.get(
                    "/api/astro-clock/forensic",
                    query_string=dict(anchor["query"]),
                )
                self.assertEqual(response.status_code, 200)
                payload = response.get_json() or {}
                self.assertTrue(payload.get("success"))
                categories = set((payload.get("scoring_categories") or {}).keys())
                self.assertTrue(expected[anchor_id].issubset(categories), msg=payload.get("categories"))
                self.assertNotIn("Disaster", categories, msg=payload.get("categories"))


if __name__ == "__main__":
    unittest.main()
